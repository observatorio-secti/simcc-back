import argparse
import csv
import time
import unicodedata
from datetime import datetime
from pathlib import Path

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


DEFAULT_OUTPUT_PATH = 'storage/production_themes_ai.csv'
DEFAULT_MODEL = 'gpt-4o-mini'
SOURCE_DOCUMENT_TITLE = (
    'Painel Temático de CT&I para a Transição Energética'
)
DOCUMENT_THEMES = [
    (
        'Energias Renováveis, Biomassa e '
        'Combustíveis Verdes'
    ),
    'Energias Renováveis nos Transportes',
    'Mercado de Carbono',
    'Exploração Mineral Sustentável',
    'Eficiência Energética',
]
DOCUMENT_THEME_SUBTHEMES = {
    DOCUMENT_THEMES[0]: [
        'energia solar',
        'energia eólica',
        'energia hidráulica',
        'energia geotérmica',
        'biomassa',
        'biogás',
        'biometano',
        'bioeletricidade',
        'biocombustíveis e combustíveis verdes',
        'hidrogênio renovável',
        'biorrefino e biorrefinarias',
        'aproveitamento energético de resíduos',
        'microrredes e geração renovável',
    ],
    DOCUMENT_THEMES[1]: [
        'mobilidade sustentável',
        'veículos elétricos e de baixa emissão',
        'infraestrutura de abastecimento e recarga',
        'combustíveis renováveis aplicados ao transporte',
        'baterias',
        'reciclagem de baterias de íon-lítio',
        (
            'componentes e tecnologias para veículos '
            'de baixa emissão'
        ),
    ],
    DOCUMENT_THEMES[2]: [
        'mercado e créditos de carbono',
        'precificação de carbono',
        'certificação',
        'rastreabilidade',
        'mensuração, relato e verificação - MRV',
        'inventários e redução de emissões',
        'metodologias de carbono',
        'monitoramento de emissões',
        (
            'soluções tecnológicas relacionadas ao '
            'mercado de carbono'
        ),
    ],
    DOCUMENT_THEMES[3]: [
        'minerais críticos',
        'metais prioritários para a transição energética',
        'terras raras',
        'prospecção e caracterização mineral',
        'extração mineral sustentável',
        'beneficiamento',
        'processamento mineral',
        'hidrometalurgia',
        'separação e refino',
        'redução e aproveitamento de resíduos e rejeitos',
        'reciclagem e recuperação de minerais',
        'descarbonização da atividade mineral',
    ],
    DOCUMENT_THEMES[4]: [
        'eficiência energética industrial',
        'geração distribuída',
        'autoprodução de energia',
        'cogeração',
        'aproveitamento energético de resíduos industriais',
        'redução do consumo energético em processos produtivos',
        'tecnologias e equipamentos de alta eficiência',
        'eficiência energética nos transportes',
    ],
}


def theme_key(value):
    text = str(value).strip().casefold()
    text = text.replace('–', '-').replace('—', '-')
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(
        char for char in normalized if not unicodedata.combining(char)
    )


THEME_LOOKUP = {
    theme_key(theme): theme
    for theme in DOCUMENT_THEMES
}
SUBTHEME_LOOKUP = {
    theme: {
        theme_key(subtheme): subtheme
        for subtheme in subthemes
    }
    for theme, subthemes in DOCUMENT_THEME_SUBTHEMES.items()
}
SUBTHEME_PARENT_LOOKUP = {
    theme_key(subtheme): theme
    for theme, subthemes in DOCUMENT_THEME_SUBTHEMES.items()
    for subtheme in subthemes
}


class ProductionThemes(BaseModel):
    main_theme: str = Field(
        description='Tema principal associado ao artigo.'
    )
    subthemes: list[str] = Field(
        description='Subtemas associados ao artigo.'
    )


def build_prompt(title, abstract):
    themes_block = '\n'.join(
        f'- {theme}\n'
        + '\n'.join(
            f'  - {subtheme}'
            for subtheme in DOCUMENT_THEME_SUBTHEMES[theme]
        )
        for theme in DOCUMENT_THEMES
    )

    return f"""
    Você é um classificador de temas de produções científicas.

    Analise o título e o resumo do artigo abaixo e classifique a produção
    nos eixos temáticos do documento "{SOURCE_DOCUMENT_TITLE}".

    Dados:
    - Título: {title}
    - Resumo: {abstract}

    Temas principais e subtemas permitidos:
    {themes_block}

    Regras:
    1. Retorne exatamente 1 tema principal, escolhido entre os 5 temas
       principais permitidos.
    2. Retorne apenas subtemas que pertençam ao tema principal escolhido, retorne de 1 a 4 subtemas.
    3. Os subtemas devem existir exatamente na lista permitida.
    4. Escolha os subtemas sustentados pelo título ou resumo. Se nenhum
       subtema for sustentado, retorne uma lista vazia.
    5. Não crie temas, subtemas, sinônimos, áreas novas ou explicações.
    6. Não use conhecimento externo sobre o artigo.
    7. É obrigatório o retorno de pelo menos 1 subtema.
    """


def normalize_main_theme(theme):
    key = theme_key(str(theme).strip().strip(';.:-'))
    return THEME_LOOKUP.get(key, '')


def infer_main_theme_from_subthemes(subthemes):
    for subtheme in subthemes or []:
        key = theme_key(str(subtheme).strip().strip(';.:-'))
        main_theme = SUBTHEME_PARENT_LOOKUP.get(key)
        if main_theme:
            return main_theme

    return ''


def normalize_subthemes(main_theme, subthemes):
    normalized = []
    seen = set()
    allowed_subthemes = SUBTHEME_LOOKUP.get(main_theme, {})

    for subtheme in subthemes or []:
        key = theme_key(str(subtheme).strip().strip(';.:-'))
        if not key:
            continue

        value = allowed_subthemes.get(key)
        if value is None:
            continue

        if key in seen:
            continue

        normalized.append(value)
        seen.add(key)

        if len(normalized) == 5:
            break

    return normalized


def list_articles(session, year_from, current_year, limit=None):
    limit_clause = ''
    if limit is not None and limit > 0:
        limit_clause = f'LIMIT {int(limit)}'

    SCRIPT_SQL = text(f"""
        SELECT DISTINCT ON (
            COALESCE(
                NULLIF(LOWER(TRIM(bp.doi)), ''),
                LOWER(TRIM(bp.title))
            )
        )
            bp.id,
            bp.title,
            oa.abstract,
            bp.doi,
            bp.year_
        FROM bibliographic_production bp
        INNER JOIN openalex_article oa ON oa.article_id = bp.id
        WHERE bp.type = 'ARTICLE'
            AND bp.year_ IS NOT NULL
            AND bp.year_ >= :year_from
            AND bp.year_ <= :current_year
            AND bp.title IS NOT NULL
            AND TRIM(bp.title) != ''
            AND oa.abstract IS NOT NULL
            AND TRIM(oa.abstract) != ''
        ORDER BY
            COALESCE(
                NULLIF(LOWER(TRIM(bp.doi)), ''),
                LOWER(TRIM(bp.title))
            ),
            bp.year_ DESC,
            bp.title ASC
        {limit_clause}
    """)
    return (
        session
        .execute(
            SCRIPT_SQL,
            {'year_from': year_from, 'current_year': current_year},
        )
        .mappings()
        .all()
    )


def write_csv(rows, output_path):
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open('w', newline='', encoding='utf-8-sig') as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                'nome_artigo',
                'abstract',
                'doi',
                'tema_principal',
                'subtemas',
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    return output_file


items_found = 0
items_succeeded = 0
items_failed = 0


def main(
    output_path=DEFAULT_OUTPUT_PATH,
    years=5,
    year_from=None,
    limit=None,
    model_name=DEFAULT_MODEL,
):
    global items_found, items_succeeded, items_failed
    session = next(get_sync_session())
    start_time = time.perf_counter()

    current_year = datetime.now().year
    min_year = (
        year_from if year_from is not None else current_year - years + 1
    )
    success_count = 0
    failed_count = 0
    csv_rows = []

    try:
        model = ChatOpenAI(
            api_key=Settings().OPENAI_API_KEY,
            model=model_name,
            temperature=0,
        )
        structured_model = model.with_structured_output(ProductionThemes)

        articles = list_articles(session, min_year, current_year, limit)
        total_articles = len(articles)
        items_found = total_articles

        routine_step_started(
            'generate_production_themes_ai_csv',
            total_items=total_articles,
            year_from=min_year,
            current_year=current_year,
            output_path=output_path,
        )

        for i, article in enumerate(articles):
            article_id = article.get('id')
            title = article.get('title')
            abstract = article.get('abstract')
            doi = article.get('doi') or ''

            try:
                response = structured_model.invoke(
                    build_prompt(title, abstract)
                )
                main_theme = normalize_main_theme(response.main_theme)
                if not main_theme:
                    main_theme = infer_main_theme_from_subthemes(
                        response.subthemes
                    )
                if not main_theme:
                    raise ValueError(
                        'Tema principal retornado fora da lista permitida.'
                    )
                subthemes = normalize_subthemes(
                    main_theme,
                    response.subthemes,
                )

                csv_rows.append({
                    'nome_artigo': title,
                    'abstract': abstract,
                    'doi': doi,
                    'tema_principal': main_theme,
                    'subtemas': '; '.join(subthemes),
                })
                success_count += 1
                logger.debug(
                    f'Production themes generated for article {article_id}',
                    title=title,
                    main_theme=main_theme,
                    subthemes=subthemes,
                )
            except Exception as e:
                failed_count += 1
                routine_item_error(
                    article_id,
                    str(e),
                    title=title,
                    doi=doi,
                )

            if (i + 1) % 20 == 0 or (i + 1) == total_articles:
                routine_progress(
                    'generate_production_themes_ai_csv',
                    i + 1,
                    total_articles,
                    success_count,
                    failed_count,
                )

        output_file = write_csv(csv_rows, output_path)
        items_succeeded = success_count
        items_failed = failed_count
        duration = time.perf_counter() - start_time

        routine_step_finished(
            'generate_production_themes_ai_csv',
            duration=duration,
            total_items=items_found,
            total_exported=items_succeeded,
            total_failed=items_failed,
            output_path=str(output_file),
        )

        print(f'CSV gerado em: {output_file}')
        print(f'Artigos encontrados: {items_found}')
        print(f'Artigos exportados: {items_succeeded}')
        print(f'Falhas: {items_failed}')

        return output_file

    except Exception:
        items_succeeded = success_count
        items_failed = items_found - items_succeeded
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=(
            'Gera CSV com temas associados a artigos dos últimos anos via IA.'
        )
    )
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT_PATH,
        help='Caminho do CSV de saída.',
    )
    parser.add_argument(
        '--years',
        type=int,
        default=5,
        help='Tamanho da janela em anos, incluindo o ano atual.',
    )
    parser.add_argument(
        '--year-from',
        type=int,
        default=None,
        help='Ano inicial explícito. Se informado, substitui --years.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limite máximo de artigos a processar.',
    )
    parser.add_argument(
        '--model',
        default=DEFAULT_MODEL,
        help='Modelo OpenAI usado para extrair os temas.',
    )
    args = parser.parse_args()

    main(
        output_path=args.output,
        years=args.years,
        year_from=args.year_from,
        limit=args.limit,
        model_name=args.model,
    )
