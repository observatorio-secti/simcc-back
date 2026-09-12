import argparse
import asyncio
import os
import sys
from typing import Optional

from pathlib import Path

# Ajusta o path para importar os módulos internos corretamente
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from simcc.ai.providers.openai_provider import OpenAIProvider
from simcc.core.db.models.ai import SearchDocumentResearcher
from simcc.core.db.models.expertise import (
    AreaExpertise,
    GreatAreaExpertise,
    SubAreaExpertise,
)
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.researcher import (
    Education,
    Researcher,
    ResearcherAreaExpertise,
    ResearcherProfessionalExperience,
)
from simcc.core.settings import Settings


async def run_ingestion(
    batch_size: int = 25,
    limit: Optional[int] = None,
    reindex: bool = False,
):
    settings = Settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    if not settings.OPENAI_API_KEY:
        print(
            '❌ [ERRO] OPENAI_API_KEY não configurada. Defina a variável no ambiente ou .env.'
        )
        return

    ai_provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY)

    async with async_session() as session:
        # 1. Contagem e Consulta Base
        count_query = select(func.count(Researcher.id))
        query = select(Researcher, Institution).outerjoin(
            Institution, Institution.id == Researcher.institution_id
        )

        if not reindex:
            query = query.outerjoin(
                SearchDocumentResearcher,
                SearchDocumentResearcher.researcher_id == Researcher.id,
            ).filter(SearchDocumentResearcher.id.is_(None))

            count_query = count_query.outerjoin(
                SearchDocumentResearcher,
                SearchDocumentResearcher.researcher_id == Researcher.id,
            ).filter(SearchDocumentResearcher.id.is_(None))

        if limit:
            query = query.limit(limit)

        total_pending = await session.scalar(count_query)
        if limit and total_pending:
            total_to_process = min(total_pending, limit)
        else:
            total_to_process = total_pending or 0

        print('=' * 75)
        print('🔬 [SIMCC] Ingestão Incremental de Pesquisadores para IA')
        print(f'📊 Registros pendentes de indexação: {total_to_process}')
        print(f'📦 Tamanho do lote de salvamento: {batch_size}')
        print(
            f'🔄 Modo reindexação forçada: {"Sim" if reindex else "Não (Incremental / Resume)"}'
        )
        print('=' * 75)

        if total_to_process == 0:
            print(
                '✨ Todos os pesquisadores já estão indexados no banco! Nada a fazer.'
            )
            return

        result = await session.execute(query)
        rows = result.all()

        processed_count = 0
        current_batch = 0

        try:
            for r, inst in rows:
                processed_count += 1
                current_batch += 1
                percent = (processed_count / total_to_process) * 100

                # 1. Instituição
                if inst:
                    inst_name = (
                        f'{inst.name} ({inst.acronym})'
                        if inst.acronym
                        else inst.name
                    )
                else:
                    inst_name = 'Instituição não informada'

                # 2. Áreas de Conhecimento
                areas_stmt = (
                    select(
                        AreaExpertise.name,
                        SubAreaExpertise.name,
                        GreatAreaExpertise.name,
                    )
                    .select_from(ResearcherAreaExpertise)
                    .outerjoin(
                        AreaExpertise,
                        AreaExpertise.id
                        == ResearcherAreaExpertise.area_expertise_id,
                    )
                    .outerjoin(
                        SubAreaExpertise,
                        SubAreaExpertise.id
                        == ResearcherAreaExpertise.sub_area_expertise_id,
                    )
                    .outerjoin(
                        GreatAreaExpertise,
                        GreatAreaExpertise.id
                        == ResearcherAreaExpertise.great_area_expertise_id,
                    )
                    .filter(ResearcherAreaExpertise.researcher_id == r.id)
                )
                areas_res = await session.execute(areas_stmt)
                areas_list = []
                for ae_name, sa_name, ga_name in areas_res.all():
                    parts = [p for p in [ga_name, ae_name, sa_name] if p]
                    if parts:
                        areas_list.append(' / '.join(parts))
                areas_str = (
                    '; '.join(areas_list) if areas_list else 'Não informada'
                )

                # 3. Formação Acadêmica
                edu_stmt = select(Education).filter(
                    Education.researcher_id == r.id
                )
                edu_res = await session.execute(edu_stmt)
                edu_list = []
                for e in edu_res.scalars().all():
                    edu_parts = [
                        e.degree or '',
                        e.education_name or '',
                        e.institution or '',
                    ]
                    edu_list.append(' - '.join([p for p in edu_parts if p]))
                edu_str = (
                    '\n'.join(edu_list)
                    if edu_list
                    else 'Conforme resumo Lattes'
                )

                # 4. Experiência e Cargos
                exp_stmt = select(ResearcherProfessionalExperience).filter(
                    ResearcherProfessionalExperience.researcher_id == r.id
                )
                exp_res = await session.execute(exp_stmt)
                exp_list = []
                for exp in exp_res.scalars().all():
                    exp_parts = [
                        exp.enterprise,
                        exp.functional_classification
                        or exp.other_functional_classification,
                        exp.additional_info,
                    ]
                    exp_list.append(' - '.join([p for p in exp_parts if p]))
                exp_str = (
                    '\n'.join(exp_list)
                    if exp_list
                    else 'Conforme resumo Lattes'
                )

                # 5. Resumo Profissional
                abstract = (
                    r.abstract or r.abstract_ai or 'Resumo não disponível'
                )

                document = (
                    f'Pesquisador: {r.name}\n'
                    f'Instituição: {inst_name}\n'
                    f'Áreas de Atuação e Especialidades: {areas_str}\n'
                    f'Formação Acadêmica:\n{edu_str}\n'
                    f'Experiência Profissional e Gestão:\n{exp_str}\n'
                    f'Resumo do Currículo Lattes:\n{abstract}\n'
                )

                # Gera embedding via OpenAI
                embedding = await ai_provider.get_embeddings(document)

                # Deleta index anterior para este pesquisador se existir (upsert)
                await session.execute(
                    delete(SearchDocumentResearcher).filter(
                        SearchDocumentResearcher.researcher_id == r.id
                    )
                )

                # Salva o novo documento
                doc = SearchDocumentResearcher(
                    researcher_id=r.id,
                    document_content=document,
                    embedding=embedding,
                )
                session.add(doc)

                print(
                    f'[{processed_count:04d}/{total_to_process:04d}] ({percent:5.1f}%) '
                    f'✓ {r.name[:35]:<35} | {inst_name[:18]:<18} | Embedding OK'
                )

                # Commit por lote para persistência segura
                if current_batch >= batch_size:
                    await session.commit()
                    print(
                        f'   💾 [LOTE SALVO] {processed_count} pesquisadores persistidos com sucesso no PostgreSQL.\n'
                    )
                    current_batch = 0

            # Commit final de qualquer sobra
            if current_batch > 0:
                await session.commit()
                print(
                    f'   💾 [LOTE FINAL SALVO] Total de {processed_count} pesquisadores persistidos.'
                )

            print('=' * 75)
            print(
                f'🎉 Ingestão de pesquisadores finalizada com sucesso! Total processado: {processed_count}'
            )
            print('=' * 75)

        except (KeyboardInterrupt, asyncio.CancelledError):
            print('\n' + '!' * 75)
            print('⚠️ Processamento pausado pelo usuário (Ctrl+C).')
            if current_batch > 0:
                await session.commit()
                print(
                    f'💾 Lote pendente ({current_batch} registros) foi salvo com sucesso!'
                )
            print(
                f'📌 Progresso total garantido: {processed_count}/{total_to_process} pesquisadores salvos no banco.'
            )
            print(
                '💡 Ao rodar o script novamente, ele continuará exatamente a partir do próximo pendente!'
            )
            print('!' * 75)


def main():
    parser = argparse.ArgumentParser(
        description='Ingestão e indexação vetorial incremental de pesquisadores para o modelo SearchDocumentResearcher'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=25,
        help='Quantidade de registros processados por lote de commit (padrão: 25)',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limite total de pesquisadores a processar nesta execução (ex: 50)',
    )
    parser.add_argument(
        '--reindex',
        action='store_true',
        default=False,
        help='Forçar reindexação de pesquisadores que já possuem embedding no banco',
    )
    args = parser.parse_args()

    asyncio.run(
        run_ingestion(
            batch_size=args.batch_size,
            limit=args.limit,
            reindex=args.reindex,
        )
    )


if __name__ == '__main__':
    main()
