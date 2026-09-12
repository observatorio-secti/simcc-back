#!/usr/bin/env python3
"""
Script de extração da amostra do banco de dados (Golden Dataset).

Extrai:
- 30 registros de search_document_researcher (e seus pesquisadores/instituições)
- 30 registros de cada tipo de search_document_production (ARTICLE, BOOK, BOOK_CHAPTER, REPORT, SOFTWARE, PATENT)
- Todas as entidades pai e detalhes para garantir integridade referencial relacional completa

Exporta:
- tests/fixtures/golden_dataset/sample_data.json (e .json.gz)
- tests/fixtures/golden_dataset/sample_data.sha256 (assinatura)
- tests/fixtures/golden_dataset/CATALOG.md (catálogo legível para inspeção manual)
"""

import argparse
import asyncio
import gzip
import hashlib
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

DEFAULT_DB_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://postgres:postgres@localhost:5433/simcc',
)
OUTPUT_DIR = PROJECT_ROOT / 'tests/fixtures/golden_dataset'


def json_serializer(obj):
    if isinstance(obj, (UUID, datetime, date)):
        return str(obj)
    if isinstance(obj, list):
        return [json_serializer(i) for i in obj]
    if isinstance(obj, dict):
        return {k: json_serializer(v) for k, v in obj.items()}
    return obj


async def extract_data(db_url: str):
    print(f'Conectando ao banco de dados: {db_url}...')
    engine = create_async_engine(db_url, echo=False)
    output_data = {}

    async with engine.connect() as conn:
        # 1. Extrair 30 pesquisadores indexados
        print('Extraindo 30 registros de search_document_researcher...')
        res_sdr = await conn.execute(text('''
            SELECT id, researcher_id, document_content, embedding, last_indexed_at
            FROM search_document_researcher
            WHERE embedding IS NOT NULL AND length(document_content) > 50
            ORDER BY last_indexed_at DESC
            LIMIT 30;
        '''))
        sdr_rows = [dict(r._mapping) for r in res_sdr.all()]
        for r in sdr_rows:
            if isinstance(r['embedding'], str):
                r['embedding'] = json.loads(r['embedding'])
        output_data['search_document_researcher'] = sdr_rows
        researcher_ids = {r['researcher_id'] for r in sdr_rows}

        # 2. Extrair até 30 registros de cada tipo de produção
        production_types = [
            'ARTICLE',
            'BOOK',
            'BOOK_CHAPTER',
            'REPORT',
            'SOFTWARE',
            'PATENT',
        ]
        sdp_rows = []
        production_ids_by_type = {t: set() for t in production_types}

        for ptype in production_types:
            print(
                f'Extraindo registros de search_document_production para tipo {ptype}...'
            )
            res_sdp = await conn.execute(text(f'''
                SELECT id, production_id, type, document_content, embedding, last_indexed_at
                FROM search_document_production
                WHERE type = '{ptype}' AND embedding IS NOT NULL
                ORDER BY last_indexed_at DESC
                LIMIT 30;
            '''))
            rows = [dict(r._mapping) for r in res_sdp.all()]
            for r in rows:
                if isinstance(r['embedding'], str):
                    r['embedding'] = json.loads(r['embedding'])
                production_ids_by_type[ptype].add(r['production_id'])
            sdp_rows.extend(rows)
            print(f'  -> {ptype}: {len(rows)} recuperados.')

        output_data['search_document_production'] = sdp_rows

        # 3. Extrair entidades pai das produções
        # 3.1 Bibliographic Productions (ARTICLE, BOOK, BOOK_CHAPTER)
        bib_ids = (
            production_ids_by_type['ARTICLE']
            | production_ids_by_type['BOOK']
            | production_ids_by_type['BOOK_CHAPTER']
        )
        if bib_ids:
            bib_ids_sql = ', '.join(f"'{bid}'" for bid in bib_ids)
            res_bp = await conn.execute(text(f'''
                SELECT id, title, type, title_en, doi, nature, year, language, 
                       means_divulgation, homepage, relevance, has_image, 
                       scientific_divulgation, researcher_id, authors, year_, is_new
                FROM bibliographic_production
                WHERE id IN ({bib_ids_sql});
            '''))
            bp_rows = [dict(r._mapping) for r in res_bp.all()]
            output_data['bibliographic_production'] = bp_rows
            researcher_ids.update(r['researcher_id'] for r in bp_rows)

            # Detalhes de Artigo
            res_art = await conn.execute(text(f'''
                SELECT id, bibliographic_production_id, periodical_magazine_id, periodical_magazine_name, 
                       issn, qualis, jcr, jcr_link, stars, quadrennial
                FROM bibliographic_production_article
                WHERE bibliographic_production_id IN ({bib_ids_sql});
            '''))
            art_rows = [dict(r._mapping) for r in res_art.all()]
            output_data['bibliographic_production_article'] = art_rows

            # Extrai periódicos referenciados
            mag_ids = {
                r['periodical_magazine_id']
                for r in art_rows
                if r.get('periodical_magazine_id')
            }
            if mag_ids:
                mag_ids_sql = ', '.join(f"'{mid}'" for mid in mag_ids)
                res_mag = await conn.execute(text(f'''
                    SELECT id, name, issn, qualis, jcr, jcr_link, reference_period
                    FROM periodical_magazine
                    WHERE id IN ({mag_ids_sql});
                '''))
                output_data['periodical_magazine'] = [
                    dict(r._mapping) for r in res_mag.all()
                ]
            else:
                output_data['periodical_magazine'] = []

            # Detalhes de Livro
            res_bk = await conn.execute(text(f'''
                SELECT id, bibliographic_production_id, isbn, qtt_volume, qtt_pages, 
                       publishing_company, publishing_company_city, stars
                FROM bibliographic_production_book
                WHERE bibliographic_production_id IN ({bib_ids_sql});
            '''))
            output_data['bibliographic_production_book'] = [
                dict(r._mapping) for r in res_bk.all()
            ]

            # Detalhes de Capítulo
            res_chp = await conn.execute(text(f'''
                SELECT id, bibliographic_production_id, book_title, isbn, organizers, 
                       publishing_company, publishing_company_city, stars
                FROM bibliographic_production_book_chapter
                WHERE bibliographic_production_id IN ({bib_ids_sql});
            '''))
            output_data['bibliographic_production_book_chapter'] = [
                dict(r._mapping) for r in res_chp.all()
            ]
        else:
            output_data['bibliographic_production'] = []
            output_data['bibliographic_production_article'] = []
            output_data['bibliographic_production_book'] = []
            output_data['bibliographic_production_book_chapter'] = []

        # 3.2 Patentes
        pat_ids = production_ids_by_type['PATENT']
        if pat_ids:
            pat_ids_sql = ', '.join(f"'{pid}'" for pid in pat_ids)
            res_pat = await conn.execute(text(f'''
                SELECT id, title, category, relevance, has_image, development_year, 
                       details, researcher_id, code, grant_date, deposit_date, is_new, stars
                FROM patent
                WHERE id IN ({pat_ids_sql});
            '''))
            pat_rows = [dict(r._mapping) for r in res_pat.all()]
            output_data['patent'] = pat_rows
            researcher_ids.update(
                r['researcher_id'] for r in pat_rows if r['researcher_id']
            )
        else:
            output_data['patent'] = []

        # 3.3 Softwares
        soft_ids = production_ids_by_type['SOFTWARE']
        if soft_ids:
            soft_ids_sql = ', '.join(f"'{sid}'" for sid in soft_ids)
            res_soft = await conn.execute(text(f'''
                SELECT id, title, platform, goal, relevance, has_image, environment, 
                       availability, researcher_id, year, is_new, stars, code
                FROM software
                WHERE id IN ({soft_ids_sql});
            '''))
            soft_rows = [dict(r._mapping) for r in res_soft.all()]
            output_data['software'] = soft_rows
            researcher_ids.update(
                r['researcher_id'] for r in soft_rows if r['researcher_id']
            )
        else:
            output_data['software'] = []

        # 3.4 Relatórios Técnicos
        rep_ids = production_ids_by_type['REPORT']
        if rep_ids:
            rep_ids_sql = ', '.join(f"'{rid}'" for rid in rep_ids)
            res_rep = await conn.execute(text(f'''
                SELECT id, researcher_id, title, project_name, year, is_new, stars
                FROM research_report
                WHERE id IN ({rep_ids_sql});
            '''))
            rep_rows = [dict(r._mapping) for r in res_rep.all()]
            output_data['research_report'] = rep_rows
            researcher_ids.update(
                r['researcher_id'] for r in rep_rows if r['researcher_id']
            )
        else:
            output_data['research_report'] = []

        # 4. Extrair todos os pesquisadores correspondentes
        valid_researcher_ids = {r for r in researcher_ids if r is not None}
        print(
            f'Extraindo {len(valid_researcher_ids)} pesquisadores vinculados...'
        )
        r_ids_sql = ', '.join(f"'{rid}'" for rid in valid_researcher_ids)
        res_r = await conn.execute(text(f'''
            SELECT id, name, lattes_id, lattes_10_id, last_update, has_image, 
                   citations, orcid, abstract, abstract_en, abstract_ai, 
                   other_information, qtt_publications, institution_id
            FROM researcher
            WHERE id IN ({r_ids_sql});
        '''))
        r_rows = [dict(r._mapping) for r in res_r.all()]
        output_data['researcher'] = r_rows

        # 5. Extrair todas as instituições correspondentes
        inst_ids = {
            r['institution_id'] for r in r_rows if r.get('institution_id')
        }
        if inst_ids:
            inst_ids_sql = ', '.join(f"'{iid}'" for iid in inst_ids)
            res_inst = await conn.execute(text(f'''
                SELECT id, name, acronym, description, lattes_id, cnpj, image, latitude, longitude
                FROM institution
                WHERE id IN ({inst_ids_sql});
            '''))
            inst_rows = [dict(r._mapping) for r in res_inst.all()]
        else:
            inst_rows = []
        output_data['institution'] = inst_rows

    await engine.dispose()
    return output_data


def generate_catalog_markdown(data: dict) -> str:
    """Gera um catálogo legível em Markdown para inspeção manual."""
    institutions_map = {
        str(i['id']): i.get('acronym') or i.get('name') or 'N/D'
        for i in data.get('institution', [])
    }
    researchers_map = {
        str(r['id']): {
            'name': r['name'],
            'institution': institutions_map.get(
                str(r.get('institution_id')), 'N/D'
            ),
            'lattes': r.get('lattes_id') or 'N/D',
        }
        for r in data.get('researcher', [])
    }

    md = []
    md.append('# 📚 Catálogo da Amostra do Banco (Golden Dataset)')
    md.append(
        '\nEste catálogo resume todos os registros extraídos para inspeção manual e elaboração dos casos de teste (`EVALUATION_CASES`).\n'
    )
    md.append('### 📊 Resumo da Amostra')
    md.append(
        f"- **Pesquisadores Indexados**: {len(data['search_document_researcher'])}"
    )
    md.append(f"- **Pesquisadores Totais (com autores)**: {len(data['researcher'])}")
    md.append(f"- **Instituições**: {len(data['institution'])}")
    md.append(f"- **Documentos de Produção**: {len(data['search_document_production'])}")
    md.append(f"  - Artigos: {len([p for p in data['search_document_production'] if p['type'] == 'ARTICLE'])}")
    md.append(f"  - Livros: {len([p for p in data['search_document_production'] if p['type'] == 'BOOK'])}")
    md.append(f"  - Capítulos: {len([p for p in data['search_document_production'] if p['type'] == 'BOOK_CHAPTER'])}")
    md.append(f"  - Relatórios Técnicos: {len([p for p in data['search_document_production'] if p['type'] == 'REPORT'])}")
    md.append(f"  - Softwares: {len([p for p in data['search_document_production'] if p['type'] == 'SOFTWARE'])}")
    md.append(f"  - Patentes: {len([p for p in data['search_document_production'] if p['type'] == 'PATENT'])}\n")
    md.append('---\n')

    # 1. Pesquisadores
    md.append('## 1. 🧑‍🔬 Pesquisadores Indexados (Amostra Direta)')
    md.append(
        '| # | Nome | Instituição | Lattes ID | Trecho do Conteúdo Indexado |'
    )
    md.append('|---|---|---|---|---|')
    for idx, doc in enumerate(data['search_document_researcher'], 1):
        r_info = researchers_map.get(
            str(doc['researcher_id']),
            {'name': 'N/D', 'institution': 'N/D', 'lattes': 'N/D'},
        )
        content_preview = (
            doc['document_content'].replace('\n', ' ')[:120] + '...'
        )
        md.append(
            f"| {idx} | **{r_info['name']}** | {r_info['institution']} | `{r_info['lattes']}` | {content_preview} |"
        )
    md.append('\n---\n')

    # 2. Produções por Tipo
    prod_type_titles = {
        'ARTICLE': '2. 📄 Artigos em Periódicos',
        'BOOK': '3. 📖 Livros',
        'BOOK_CHAPTER': '4. 📑 Capítulos de Livros',
        'REPORT': '5. 📋 Relatórios Técnicos',
        'SOFTWARE': '6. 💻 Softwares e Sistemas',
        'PATENT': '7. 💡 Patentes e Registros',
    }

    bp_map = {str(b['id']): b for b in data.get('bibliographic_production', [])}
    pat_map = {str(p['id']): p for p in data.get('patent', [])}
    soft_map = {str(s['id']): s for s in data.get('software', [])}
    rep_map = {str(r['id']): r for r in data.get('research_report', [])}

    for ptype in [
        'ARTICLE',
        'BOOK',
        'BOOK_CHAPTER',
        'REPORT',
        'SOFTWARE',
        'PATENT',
    ]:
        docs_of_type = [
            p for p in data['search_document_production'] if p['type'] == ptype
        ]
        md.append(f"## {prod_type_titles.get(ptype, ptype)}")
        md.append('| # | Título | Ano | Autores / Pesquisador | Conteúdo Semântico Indexado |')
        md.append('|---|---|---|---|---|')

        for idx, doc in enumerate(docs_of_type, 1):
            pid = str(doc['production_id'])
            title = 'N/D'
            year = 'N/D'
            authors = 'N/D'

            if ptype in ['ARTICLE', 'BOOK', 'BOOK_CHAPTER']:
                bp = bp_map.get(pid)
                if bp:
                    title = bp.get('title') or 'N/D'
                    year = bp.get('year') or bp.get('year_') or 'N/D'
                    authors = (
                        bp.get('authors')
                        or researchers_map.get(
                            str(bp.get('researcher_id')), {}
                        ).get('name')
                        or 'N/D'
                    )
            elif ptype == 'PATENT':
                pat = pat_map.get(pid)
                if pat:
                    title = pat.get('title') or 'N/D'
                    year = pat.get('development_year') or 'N/D'
                    authors = researchers_map.get(
                        str(pat.get('researcher_id')), {}
                    ).get('name', 'N/D')
            elif ptype == 'SOFTWARE':
                soft = soft_map.get(pid)
                if soft:
                    title = soft.get('title') or 'N/D'
                    year = soft.get('year') or 'N/D'
                    authors = researchers_map.get(
                        str(soft.get('researcher_id')), {}
                    ).get('name', 'N/D')
            elif ptype == 'REPORT':
                rep = rep_map.get(pid)
                if rep:
                    title = rep.get('title') or 'N/D'
                    year = rep.get('year') or 'N/D'
                    authors = researchers_map.get(
                        str(rep.get('researcher_id')), {}
                    ).get('name', 'N/D')

            preview = doc['document_content'].replace('\n', ' ')[:100] + '...'
            title_clean = title.replace('|', '-').strip()
            md.append(f'| {idx} | {title_clean} | {year} | {authors} | {preview} |')

        md.append('\n---\n')

    return '\n'.join(md)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Extrair Golden Dataset de produções e pesquisadores do banco de dados'
    )
    parser.add_argument(
        '--db-url',
        type=str,
        default=os.getenv('DATABASE_URL', DEFAULT_DB_URL),
        help=f'URL do banco de dados (padrão: DATABASE_URL ou {DEFAULT_DB_URL})',
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=OUTPUT_DIR,
        help=f'Diretório de saída (padrão: {OUTPUT_DIR})',
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    extracted_data = await extract_data(args.db_url)

    # 1. Salvar JSON
    json_path = args.output_dir / 'sample_data.json'
    print(f'Salvando JSON em: {json_path}...')
    serialized_data = json_serializer(extracted_data)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(serialized_data, f, ensure_ascii=False, indent=2)

    raw_size_mb = json_path.stat().st_size / (1024 * 1024)
    print(f'  -> Tamanho JSON: {raw_size_mb:.2f} MB')

    # 2. Salvar GZIP (menor espaço possível para Git se desejado)
    gz_path = args.output_dir / 'sample_data.json.gz'
    print(f'Compactando em GZIP: {gz_path}...')
    with gzip.open(gz_path, 'wt', encoding='utf-8') as f_gz:
        json.dump(serialized_data, f_gz, ensure_ascii=False)

    gz_size_kb = gz_path.stat().st_size / 1024
    print(f'  -> Tamanho GZIP: {gz_size_kb:.1f} KB')

    # 3. Gerar Hash SHA-256 (Assinatura de Integridade)
    sha256_path = args.output_dir / 'sample_data.sha256'
    with open(json_path, 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    with open(sha256_path, 'w', encoding='utf-8') as f:
        f.write(digest + '\n')
    print(f'Assinatura SHA-256 gerada ({sha256_path}): {digest[:16]}...')

    # 4. Gerar Catálogo Markdown para Inspeção Humana
    catalog_path = args.output_dir / 'CATALOG.md'
    print(f'Gerando catálogo de inspeção em: {catalog_path}...')
    catalog_md = generate_catalog_markdown(extracted_data)
    with open(catalog_path, 'w', encoding='utf-8') as f:
        f.write(catalog_md)

    print(
        '\n✅ Extração concluída com sucesso! Todos os arquivos foram gerados.'
    )


if __name__ == '__main__':
    asyncio.run(main())
