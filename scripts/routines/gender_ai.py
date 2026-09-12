import argparse
import time
from typing import Literal, Optional
from uuid import UUID

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import text

from simcc.core.db.database import get_sync_session
from simcc.core.logging import logger
from simcc.core.logging.events import (
    routine_item_error,
    routine_progress,
    routine_step_finished,
    routine_step_started,
)
from simcc.core.settings import Settings

GenderLabel = Literal[
    'Homem Cis',
    'Mulher Cis',
    'Homem Trans',
    'Mulher Trans',
    'Não Informado',
]

VALID_GENDERS = {
    'Homem Cis',
    'Mulher Cis',
    'Homem Trans',
    'Mulher Trans',
    'Não Informado',
}

# Preços oficiais OpenAI para gpt-4o-mini (por 1M de tokens)
GPT_4O_MINI_INPUT_PRICE_PER_1M = 0.150
GPT_4O_MINI_OUTPUT_PRICE_PER_1M = 0.600
USD_TO_BRL_RATE = 5.70


def calculate_llm_cost(
    input_tokens: int,
    output_tokens: int,
    usd_to_brl: float = USD_TO_BRL_RATE,
) -> dict:
    """Calcula o custo total em USD e BRL a partir dos tokens consumidos."""
    cost_input_usd = (
        input_tokens * GPT_4O_MINI_INPUT_PRICE_PER_1M
    ) / 1_000_000
    cost_output_usd = (
        output_tokens * GPT_4O_MINI_OUTPUT_PRICE_PER_1M
    ) / 1_000_000
    total_cost_usd = cost_input_usd + cost_output_usd
    total_cost_brl = total_cost_usd * usd_to_brl
    return {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens,
        'cost_usd': total_cost_usd,
        'cost_brl': total_cost_brl,
    }


class GenderInference(BaseModel):
    gender: GenderLabel = Field(
        description='Gênero inferido a partir dos indícios disponíveis.'
    )
    reason: str = Field(
        description='Justificativa curta baseada apenas no texto fornecido.'
    )


def build_prompt(researcher_name, researcher_abstract):
    return f"""
    Você é um classificador de registros acadêmicos.

    Sua tarefa é analisar o nome e o resumo do currículo de uma pessoa
    pesquisadora e inferir a categoria de gênero mais provável para
    persistência no banco de dados.

    Categorias permitidas:
    - Homem Cis
    - Mulher Cis
    - Homem Trans
    - Mulher Trans
    - Não Informado

    Dados:
    - Nome: {researcher_name}
    - Resumo: {researcher_abstract}

    Regras obrigatórias:
    1. Use o conjunto de indícios disponíveis no nome e no resumo: nome próprio,
       pronomes, flexões gramaticais, títulos acadêmicos/profissionais
       (professor/professora, pesquisador/pesquisadora, coordenador/
       coordenadora etc.) e autoidentificações.
    2. Quando os indícios forem consistentes com gênero masculino e não houver
       menção explícita de identidade trans, classifique como Homem Cis.
    3. Quando os indícios forem consistentes com gênero feminino e não houver
       menção explícita de identidade trans, classifique como Mulher Cis.
    4. Classifique como Homem Trans ou Mulher Trans somente quando o resumo
       trouxer evidência textual explícita de autoidentificação como pessoa
       trans, transgênera ou transexual.
    5. Se houver ambiguidade relevante, sinais conflitantes, nome incomum sem
       apoio textual, iniciais no lugar de nome próprio ou resumo insuficiente,
       retorne Não Informado.
    6. Não use área acadêmica, instituição, nacionalidade ou aparência como
       evidência.
    7. A resposta deve usar exatamente uma das categorias permitidas.
    """


def normalize_gender(value):
    if not value:
        return 'Não Informado'

    normalized = str(value).strip()
    return normalized if normalized in VALID_GENDERS else 'Não Informado'


items_found = 0
items_succeeded = 0
items_failed = 0


def main(
    researcher_ids=None,
    lattes_ids=None,
    overwrite=False,
    limit: Optional[int] = None,
):
    global items_found, items_succeeded, items_failed
    session = next(get_sync_session())
    start_time = time.perf_counter()

    success_count = 0
    failed_count = 0
    total_input_tokens = 0
    total_output_tokens = 0

    try:
        model = ChatOpenAI(
            api_key=Settings().OPENAI_API_KEY,
            model='gpt-4o-mini',
            temperature=0,
        )
        structured_model = model.with_structured_output(
            GenderInference, include_raw=True
        )

        researcher_filter = ''
        query_params = {}
        if researcher_ids:
            researcher_filter += ' AND r.id = ANY(:researcher_ids)'
            query_params['researcher_ids'] = [
                UUID(str(rid)) for rid in researcher_ids
            ]
        if lattes_ids:
            researcher_filter += ' AND r.lattes_id = ANY(:lattes_ids)'
            query_params['lattes_ids'] = list(lattes_ids)
        if not overwrite:
            researcher_filter += """
                AND (
                    rca.gender IS NULL
                    OR TRIM(rca.gender) = ''
                )
            """

        has_rca = session.scalar(
            text("SELECT to_regclass('researcher_custom_attributes')")
        )
        if not has_rca:
            print("Tabela researcher_custom_attributes foi descontinuada.")
            return

        limit_clause = ''
        if limit is not None and limit > 0:
            limit_clause = f'LIMIT {int(limit)}'

        SCRIPT_SQL_RESEARCHERS = text(f"""
            SELECT r.id, r.name, r.lattes_id, r.abstract, rca.gender
            FROM researcher r
            LEFT JOIN researcher_custom_attributes rca ON rca.researcher_id = r.id
            WHERE 1 = 1 {researcher_filter}
            ORDER BY r.name ASC
            {limit_clause}
        """)
        researchers_to_process = (
            session
            .execute(SCRIPT_SQL_RESEARCHERS, query_params)
            .mappings()
            .all()
        )

        total_researchers = len(researchers_to_process)
        items_found = total_researchers

        routine_step_started(
            'infer_researcher_gender_ai',
            total_items=total_researchers,
        )

        SCRIPT_UPSERT = text("""
            INSERT INTO researcher_custom_attributes (
                researcher_id, gender
            )
            VALUES (
                :researcher_id, :gender
            )
            ON CONFLICT (researcher_id) DO UPDATE SET
                gender = EXCLUDED.gender;
        """)

        for i, researcher_data in enumerate(researchers_to_process):
            researcher_id = researcher_data.get('id')
            lattes_id = researcher_data.get('lattes_id')
            researcher_name = researcher_data.get('name', 'N/A')
            researcher_abstract = (
                researcher_data.get('abstract') or 'Sem resumo disponível.'
            )

            try:
                if researcher_abstract == 'Sem resumo disponível.':
                    gender = 'Não Informado'
                    reason = 'Resumo ausente.'
                else:
                    prompt = build_prompt(
                        researcher_name,
                        researcher_abstract,
                    )
                    response = structured_model.invoke(prompt)

                    parsed = response.get('parsed')
                    if parsed is None:
                        gender = 'Não Informado'
                        reason = 'Falha no parsing estruturado.'
                    else:
                        gender = normalize_gender(parsed.gender)
                        reason = parsed.reason

                    raw = response.get('raw')
                    if (
                        raw
                        and hasattr(raw, 'usage_metadata')
                        and raw.usage_metadata
                    ):
                        usage = raw.usage_metadata
                        in_tok = usage.get('input_tokens', 0)
                        out_tok = usage.get('output_tokens', 0)
                        total_input_tokens += in_tok
                        total_output_tokens += out_tok
                    elif (
                        raw
                        and hasattr(raw, 'response_metadata')
                        and raw.response_metadata
                    ):
                        token_usage = raw.response_metadata.get(
                            'token_usage', {}
                        )
                        in_tok = token_usage.get('prompt_tokens', 0)
                        out_tok = token_usage.get('completion_tokens', 0)
                        total_input_tokens += in_tok
                        total_output_tokens += out_tok

                session.execute(
                    SCRIPT_UPSERT,
                    {'researcher_id': researcher_id, 'gender': gender},
                )
                session.commit()
                success_count += 1
                logger.debug(
                    'Gender inferred for researcher '
                    f'{researcher_name} ({researcher_id}): {gender}',
                    reason=reason,
                )
            except Exception as e:
                session.rollback()
                failed_count += 1
                routine_item_error(
                    researcher_id,
                    str(e),
                    researcher_name=researcher_name,
                    lattes_id=lattes_id,
                )

            if (i + 1) % 20 == 0 or (i + 1) == total_researchers:
                routine_progress(
                    'infer_researcher_gender',
                    i + 1,
                    total_researchers,
                    success_count,
                    failed_count,
                )

        items_succeeded = success_count
        items_failed = failed_count
        duration = time.perf_counter() - start_time
        cost_info = calculate_llm_cost(total_input_tokens, total_output_tokens)

        routine_step_finished(
            'infer_researcher_gender',
            duration=duration,
            total_updated=items_succeeded,
            total_failed=items_failed,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            total_tokens=cost_info['total_tokens'],
            cost_usd=cost_info['cost_usd'],
            cost_brl=cost_info['cost_brl'],
        )

        print('\n' + '=' * 65)
        print('RELATÓRIO DE INFERÊNCIA DE GÊNERO & CUSTOS (gpt-4o-mini)')
        print('=' * 65)
        print(f'Total de pesquisadores avaliados:    {items_found}')
        print(f'Processados com sucesso:             {items_succeeded}')
        print(f'Falhas:                              {items_failed}')
        print(f'Tempo total de execução:             {duration:.2f}s')
        print('-' * 65)
        print(f'Tokens de Entrada (Prompt):          {total_input_tokens:,}')
        print(f'Tokens de Saída (Completion):        {total_output_tokens:,}')
        print(
            f'Total de Tokens Consumidos:          {cost_info["total_tokens"]:,}'
        )
        print(
            f'Custo Total Estimado (USD):          ${cost_info["cost_usd"]:.6f}'
        )
        print(
            f'Custo Total Estimado (BRL):          R$ {cost_info["cost_brl"]:.4f} (cotação ref. R$ {USD_TO_BRL_RATE:.2f})'
        )
        if items_succeeded > 0:
            avg_cost = cost_info['cost_usd'] / items_succeeded
            print(
                f'Custo Médio por Pesquisador:         ${avg_cost:.6f} USD (~R$ {avg_cost * USD_TO_BRL_RATE:.4f})'
            )
        print('=' * 65 + '\n')

        return {
            'items_found': items_found,
            'items_succeeded': items_succeeded,
            'items_failed': items_failed,
            'duration': duration,
            'cost_info': cost_info,
        }

    except Exception:
        items_succeeded = success_count
        items_failed = items_found - items_succeeded
        session.rollback()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Rotina de inferência de gênero de pesquisadores via IA'
    )
    parser.add_argument(
        '--researcher-ids',
        nargs='+',
        type=str,
        default=None,
        help='Lista de IDs de pesquisadores para processar.',
    )
    parser.add_argument(
        '--lattes-ids',
        nargs='+',
        type=str,
        default=None,
        help='Lista de Lattes IDs para processar.',
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Reprocessa pesquisadores que já possuem genero preenchido.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limite máximo de pesquisadores a serem processados.',
    )
    args = parser.parse_args()

    main(
        researcher_ids=args.researcher_ids,
        lattes_ids=args.lattes_ids,
        overwrite=args.overwrite,
        limit=args.limit,
    )
