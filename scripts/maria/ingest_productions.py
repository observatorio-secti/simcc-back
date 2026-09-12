import argparse
import asyncio
import os
import sys
from typing import List, Optional

from pathlib import Path

# Ajusta o path para importar os módulos internos corretamente
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from simcc.ai.providers.openai_provider import OpenAIProvider
from simcc.core.db.models.ai import SearchDocumentProduction
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.production import (
    BibliographicProduction,
    BibliographicProductionArticle,
    BibliographicProductionBook,
    BibliographicProductionBookChapter,
    Patent,
    ResearchReport,
    Software,
)
from simcc.core.db.models.researcher import Researcher
from simcc.core.settings import Settings


async def process_type_records(
    session: AsyncSession,
    ai_provider: OpenAIProvider,
    type_name: str,
    query,
    count_query,
    format_doc_fn,
    batch_size: int,
    limit: Optional[int],
    reindex: bool,
) -> int:
    total_pending = await session.scalar(count_query)
    if limit and total_pending:
        total_to_process = min(total_pending, limit)
    else:
        total_to_process = total_pending or 0

    print(f'\n--- [Processando {type_name}] ---')
    print(f'📊 Registros pendentes: {total_to_process} | Lote: {batch_size}')

    if total_to_process == 0:
        print(f'✨ Todos os registros de {type_name} já estão indexados!')
        return 0

    if limit:
        query = query.limit(limit)

    result = await session.execute(query)
    rows = result.all()

    processed_count = 0
    current_batch = 0

    try:
        for row in rows:
            processed_count += 1
            current_batch += 1
            percent = (processed_count / total_to_process) * 100

            prod_id, prod_type, title, document = format_doc_fn(row)

            # Gera embedding
            embedding = await ai_provider.get_embeddings(document)

            # Upsert
            await session.execute(
                delete(SearchDocumentProduction).filter(
                    SearchDocumentProduction.production_id == prod_id
                )
            )

            doc = SearchDocumentProduction(
                production_id=prod_id,
                type=prod_type,
                document_content=document,
                embedding=embedding,
            )
            session.add(doc)

            title_display = (title or 'Sem título')[:40]
            print(
                f'[{processed_count:04d}/{total_to_process:04d}] ({percent:5.1f}%) '
                f'✓ {title_display:<40} | Embedding OK'
            )

            if current_batch >= batch_size:
                await session.commit()
                print(
                    f'   💾 [LOTE SALVO] {processed_count} itens de {type_name} persistidos no PostgreSQL.'
                )
                current_batch = 0

        if current_batch > 0:
            await session.commit()
            print(
                f'   💾 [LOTE FINAL SALVO] Total de {processed_count} itens de {type_name} persistidos.'
            )

        return processed_count

    except (KeyboardInterrupt, asyncio.CancelledError):
        if current_batch > 0:
            await session.commit()
            print(
                f'\n💾 Lote pendente ({current_batch} registros de {type_name}) salvo com sucesso!'
            )
        print(
            f'📌 Progresso garantido em {type_name}: {processed_count}/{total_to_process} salvos.'
        )
        raise


async def run_ingestion(
    types: Optional[List[str]] = None,
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
    active_types = [t.upper() for t in types] if types else []

    print('=' * 75)
    print('📚 [SIMCC] Ingestão Incremental de Produções Científicas para IA')
    print(f'📦 Tamanho do lote de salvamento: {batch_size}')
    print(
        f'🔄 Modo reindexação forçada: {"Sim" if reindex else "Não (Incremental / Resume)"}'
    )
    print(
        f'🎯 Tipos selecionados: {", ".join(active_types) if active_types else "TODOS"}'
    )
    print('=' * 75)

    total_all_types = 0

    try:
        async with async_session() as session:
            # 1. ARTIGOS
            if not active_types or 'ARTICLE' in active_types:
                stmt = (
                    select(
                        BibliographicProduction,
                        BibliographicProductionArticle,
                        Researcher,
                        Institution,
                    )
                    .join(
                        Researcher,
                        Researcher.id == BibliographicProduction.researcher_id,
                    )
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                    .outerjoin(
                        BibliographicProductionArticle,
                        BibliographicProductionArticle.bibliographic_production_id
                        == BibliographicProduction.id,
                    )
                    .filter(BibliographicProduction.type == 'ARTICLE')
                )
                c_stmt = select(func.count(BibliographicProduction.id)).filter(
                    BibliographicProduction.type == 'ARTICLE'
                )

                if not reindex:
                    stmt = stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id
                        == BibliographicProduction.id,
                    ).filter(SearchDocumentProduction.id.is_(None))
                    c_stmt = c_stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id
                        == BibliographicProduction.id,
                    ).filter(SearchDocumentProduction.id.is_(None))

                def format_article(row):
                    bp, art, r, inst = row
                    inst_name = (
                        f'{inst.name} ({inst.acronym})'
                        if (inst and inst.acronym)
                        else (inst.name if inst else 'Não informada')
                    )
                    periodical = art.periodical_magazine_name if art else ''
                    qualis = art.qualis if art else ''
                    doi = bp.doi or ''
                    year = bp.year or (str(bp.year_) if bp.year_ else '')
                    doc = (
                        f'Tipo: Artigo Publicado\n'
                        f'Título: {bp.title}\n'
                        f'Autores: {bp.authors or r.name}\n'
                        f'Pesquisador Responsável: {r.name}\n'
                        f'Instituição: {inst_name}\n'
                        f'Ano: {year}\n'
                        f'Periódico/Revista: {periodical}\n'
                        f'Qualis: {qualis}\n'
                        f'DOI: {doi}\n'
                    )
                    return bp.id, 'ARTICLE', bp.title, doc

                total_all_types += await process_type_records(
                    session,
                    ai_provider,
                    'Artigos',
                    stmt,
                    c_stmt,
                    format_article,
                    batch_size,
                    limit,
                    reindex,
                )

            # 2. LIVROS
            if not active_types or 'BOOK' in active_types:
                stmt = (
                    select(
                        BibliographicProduction,
                        BibliographicProductionBook,
                        Researcher,
                        Institution,
                    )
                    .join(
                        Researcher,
                        Researcher.id == BibliographicProduction.researcher_id,
                    )
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                    .outerjoin(
                        BibliographicProductionBook,
                        BibliographicProductionBook.bibliographic_production_id
                        == BibliographicProduction.id,
                    )
                    .filter(BibliographicProduction.type == 'BOOK')
                )
                c_stmt = select(func.count(BibliographicProduction.id)).filter(
                    BibliographicProduction.type == 'BOOK'
                )

                if not reindex:
                    stmt = stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id
                        == BibliographicProduction.id,
                    ).filter(SearchDocumentProduction.id.is_(None))
                    c_stmt = c_stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id
                        == BibliographicProduction.id,
                    ).filter(SearchDocumentProduction.id.is_(None))

                def format_book(row):
                    bp, bk, r, inst = row
                    inst_name = (
                        f'{inst.name} ({inst.acronym})'
                        if (inst and inst.acronym)
                        else (inst.name if inst else 'Não informada')
                    )
                    publisher = bk.publishing_company if bk else ''
                    isbn = bk.isbn if bk else ''
                    year = bp.year or (str(bp.year_) if bp.year_ else '')
                    doc = (
                        f'Tipo: Livro Publicado\n'
                        f'Título: {bp.title}\n'
                        f'Autores: {bp.authors or r.name}\n'
                        f'Pesquisador Responsável: {r.name}\n'
                        f'Instituição: {inst_name}\n'
                        f'Ano: {year}\n'
                        f'Editora: {publisher}\n'
                        f'ISBN: {isbn}\n'
                    )
                    return bp.id, 'BOOK', bp.title, doc

                total_all_types += await process_type_records(
                    session,
                    ai_provider,
                    'Livros',
                    stmt,
                    c_stmt,
                    format_book,
                    batch_size,
                    limit,
                    reindex,
                )

            # 3. CAPÍTULOS DE LIVROS
            if not active_types or 'BOOK_CHAPTER' in active_types:
                stmt = (
                    select(
                        BibliographicProduction,
                        BibliographicProductionBookChapter,
                        Researcher,
                        Institution,
                    )
                    .join(
                        Researcher,
                        Researcher.id == BibliographicProduction.researcher_id,
                    )
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                    .outerjoin(
                        BibliographicProductionBookChapter,
                        BibliographicProductionBookChapter.bibliographic_production_id
                        == BibliographicProduction.id,
                    )
                    .filter(BibliographicProduction.type == 'BOOK_CHAPTER')
                )
                c_stmt = select(func.count(BibliographicProduction.id)).filter(
                    BibliographicProduction.type == 'BOOK_CHAPTER'
                )

                if not reindex:
                    stmt = stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id
                        == BibliographicProduction.id,
                    ).filter(SearchDocumentProduction.id.is_(None))
                    c_stmt = c_stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id
                        == BibliographicProduction.id,
                    ).filter(SearchDocumentProduction.id.is_(None))

                def format_chapter(row):
                    bp, chp, r, inst = row
                    inst_name = (
                        f'{inst.name} ({inst.acronym})'
                        if (inst and inst.acronym)
                        else (inst.name if inst else 'Não informada')
                    )
                    book_title = chp.book_title if chp else ''
                    publisher = chp.publishing_company if chp else ''
                    organizers = chp.organizers if chp else ''
                    isbn = chp.isbn if chp else ''
                    year = bp.year or (str(bp.year_) if bp.year_ else '')
                    doc = (
                        f'Tipo: Capítulo de Livro\n'
                        f'Título do Capítulo: {bp.title}\n'
                        f'Livro: {book_title}\n'
                        f'Organizadores: {organizers}\n'
                        f'Autores: {bp.authors or r.name}\n'
                        f'Pesquisador Responsável: {r.name}\n'
                        f'Instituição: {inst_name}\n'
                        f'Ano: {year}\n'
                        f'Editora: {publisher}\n'
                        f'ISBN: {isbn}\n'
                    )
                    return bp.id, 'BOOK_CHAPTER', bp.title, doc

                total_all_types += await process_type_records(
                    session,
                    ai_provider,
                    'Capítulos de Livros',
                    stmt,
                    c_stmt,
                    format_chapter,
                    batch_size,
                    limit,
                    reindex,
                )

            # 4. PATENTES
            if not active_types or 'PATENT' in active_types:
                stmt = (
                    select(Patent, Researcher, Institution)
                    .join(Researcher, Researcher.id == Patent.researcher_id)
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                )
                c_stmt = select(func.count(Patent.id))

                if not reindex:
                    stmt = stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id == Patent.id,
                    ).filter(SearchDocumentProduction.id.is_(None))
                    c_stmt = c_stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id == Patent.id,
                    ).filter(SearchDocumentProduction.id.is_(None))

                def format_patent(row):
                    pat, r, inst = row
                    inst_name = (
                        f'{inst.name} ({inst.acronym})'
                        if (inst and inst.acronym)
                        else (inst.name if inst else 'Não informada')
                    )
                    year = pat.development_year or (
                        pat.deposit_date[:4] if pat.deposit_date else ''
                    )
                    doc = (
                        f'Tipo: Patente\n'
                        f'Título: {pat.title or "Patente"}\n'
                        f'Categoria: {pat.category or ""}\n'
                        f'Código: {pat.code or ""}\n'
                        f'Detalhes/Resumo: {pat.details or ""}\n'
                        f'Pesquisador/Inventor: {r.name}\n'
                        f'Instituição: {inst_name}\n'
                        f'Ano: {year}\n'
                    )
                    return pat.id, 'PATENT', pat.title, doc

                total_all_types += await process_type_records(
                    session,
                    ai_provider,
                    'Patentes',
                    stmt,
                    c_stmt,
                    format_patent,
                    batch_size,
                    limit,
                    reindex,
                )

            # 5. SOFTWARES
            if not active_types or 'SOFTWARE' in active_types:
                stmt = (
                    select(Software, Researcher, Institution)
                    .join(Researcher, Researcher.id == Software.researcher_id)
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                )
                c_stmt = select(func.count(Software.id))

                if not reindex:
                    stmt = stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id == Software.id,
                    ).filter(SearchDocumentProduction.id.is_(None))
                    c_stmt = c_stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id == Software.id,
                    ).filter(SearchDocumentProduction.id.is_(None))

                def format_software(row):
                    sft, r, inst = row
                    inst_name = (
                        f'{inst.name} ({inst.acronym})'
                        if (inst and inst.acronym)
                        else (inst.name if inst else 'Não informada')
                    )
                    year = str(sft.year) if sft.year else ''
                    doc = (
                        f'Tipo: Software / Programa de Computador\n'
                        f'Título: {sft.title or "Software"}\n'
                        f'Plataforma/Ambiente: {sft.platform or ""} / {sft.environment or ""}\n'
                        f'Objetivo/Finalidade: {sft.goal or ""}\n'
                        f'Financiador: {sft.financing_institutionc or ""}\n'
                        f'Pesquisador Responsável: {r.name}\n'
                        f'Instituição: {inst_name}\n'
                        f'Ano: {year}\n'
                    )
                    return sft.id, 'SOFTWARE', sft.title, doc

                total_all_types += await process_type_records(
                    session,
                    ai_provider,
                    'Softwares',
                    stmt,
                    c_stmt,
                    format_software,
                    batch_size,
                    limit,
                    reindex,
                )

            # 6. RELATÓRIOS TÉCNICOS
            if not active_types or 'REPORT' in active_types:
                stmt = (
                    select(ResearchReport, Researcher, Institution)
                    .join(
                        Researcher,
                        Researcher.id == ResearchReport.researcher_id,
                    )
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                )
                c_stmt = select(func.count(ResearchReport.id))

                if not reindex:
                    stmt = stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id
                        == ResearchReport.id,
                    ).filter(SearchDocumentProduction.id.is_(None))
                    c_stmt = c_stmt.outerjoin(
                        SearchDocumentProduction,
                        SearchDocumentProduction.production_id
                        == ResearchReport.id,
                    ).filter(SearchDocumentProduction.id.is_(None))

                def format_report(row):
                    rep, r, inst = row
                    inst_name = (
                        f'{inst.name} ({inst.acronym})'
                        if (inst and inst.acronym)
                        else (inst.name if inst else 'Não informada')
                    )
                    year = str(rep.year) if rep.year else ''
                    doc = (
                        f'Tipo: Relatório Técnico ou Científico\n'
                        f'Título: {rep.title or "Relatório Técnico"}\n'
                        f'Projeto: {rep.project_name or ""}\n'
                        f'Financiador: {rep.financing_institutionc or ""}\n'
                        f'Pesquisador Responsável: {r.name}\n'
                        f'Instituição: {inst_name}\n'
                        f'Ano: {year}\n'
                    )
                    return rep.id, 'REPORT', rep.title, doc

                total_all_types += await process_type_records(
                    session,
                    ai_provider,
                    'Relatórios Técnicos',
                    stmt,
                    c_stmt,
                    format_report,
                    batch_size,
                    limit,
                    reindex,
                )

        print('\n' + '=' * 75)
        print(
            f'🎉 Ingestão de produções finalizada! Total geral processado: {total_all_types}'
        )
        print('=' * 75)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print('\n' + '!' * 75)
        print(
            '⚠️ Processamento geral de produções pausado pelo usuário (Ctrl+C).'
        )
        print(
            f'📌 Progresso salvo no PostgreSQL: {total_all_types} produções garantidas.'
        )
        print(
            '💡 Ao rodar o script novamente, ele continuará exatamente das produções pendentes!'
        )
        print('!' * 75)


def main():
    parser = argparse.ArgumentParser(
        description='Ingestão e indexação vetorial incremental de produções científicas para o modelo SearchDocumentProduction'
    )
    parser.add_argument(
        '--types',
        type=str,
        default=None,
        help='Tipos de produção separados por vírgula (ex: ARTICLE,BOOK,BOOK_CHAPTER,PATENT,SOFTWARE,REPORT)',
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
        help='Limite de produções a processar por tipo (ex: 50)',
    )
    parser.add_argument(
        '--reindex',
        action='store_true',
        default=False,
        help='Forçar reindexação de produções que já possuem embedding no banco',
    )
    args = parser.parse_args()

    selected_types = (
        [t.strip() for t in args.types.split(',') if t.strip()]
        if args.types
        else None
    )

    asyncio.run(
        run_ingestion(
            types=selected_types,
            batch_size=args.batch_size,
            limit=args.limit,
            reindex=args.reindex,
        )
    )


if __name__ == '__main__':
    main()
