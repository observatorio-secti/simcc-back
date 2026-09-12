#!/usr/bin/env python3
"""
Script para anexar/popular a base da amostra (Golden Dataset) em qualquer banco de dados PostgreSQL com pgvector.

Uso:
  poetry run python scripts/maria/seed_golden_sample.py [--db-url URL]

Pode ser usado tanto manualmente quanto importado como função em fixtures do pytest.
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

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

DEFAULT_FIXTURE_PATH = PROJECT_ROOT / 'tests/fixtures/golden_dataset/sample_data.json'
DEFAULT_GZ_PATH = PROJECT_ROOT / 'tests/fixtures/golden_dataset/sample_data.json.gz'
DEFAULT_HASH_PATH = PROJECT_ROOT / 'tests/fixtures/golden_dataset/sample_data.sha256'


def load_dataset(fixture_path: Path = DEFAULT_FIXTURE_PATH) -> dict:
    """Carrega os dados da fixture (JSON ou GZ) e valida assinatura se existir."""
    if fixture_path.exists():
        with open(fixture_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if DEFAULT_HASH_PATH.exists():
            with open(DEFAULT_HASH_PATH, 'r', encoding='utf-8') as f_h:
                expected_hash = f_h.read().strip()
            current_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            if current_hash != expected_hash:
                print(
                    f'⚠️ AVISO: Checksum SHA-256 não coincide!\nEsperado: {expected_hash}\nAtual:    {current_hash}'
                )
            else:
                print('🔒 Assinatura SHA-256 da base validada com sucesso.')
        return json.loads(content)
    elif DEFAULT_GZ_PATH.exists():
        print(f'Lendo fixture comprimida: {DEFAULT_GZ_PATH}...')
        with gzip.open(DEFAULT_GZ_PATH, 'rt', encoding='utf-8') as f_gz:
            return json.load(f_gz)
    else:
        raise FileNotFoundError(
            f'Nenhuma fixture encontrada em {fixture_path} ou {DEFAULT_GZ_PATH}'
        )


def parse_dt(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        return val
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


async def seed_golden_dataset(
    db_url: str, fixture_path: Path = DEFAULT_FIXTURE_PATH
):
    """Insere todas as entidades da amostra no banco de dados respeitando ordem de chaves."""
    data = load_dataset(fixture_path)
    engine = create_async_engine(db_url, echo=False)

    print(f'Conectando ao banco de dados: {db_url}...')
    async with engine.begin() as conn:
        # Garante extensão pgvector
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))

        # 1. Institutions
        institutions = data.get('institution', [])
        print(f'Inserindo {len(institutions)} instituições...')
        for inst in institutions:
            await conn.execute(
                text('''
                INSERT INTO institution (id, name, acronym, description, lattes_id, cnpj, image, latitude, longitude)
                VALUES (:id, :name, :acronym, :description, :lattes_id, :cnpj, :image, :latitude, :longitude)
                ON CONFLICT (id) DO NOTHING;
            '''),
                inst,
            )

        # 2. Researchers
        researchers = data.get('researcher', [])
        print(f'Inserindo {len(researchers)} pesquisadores...')
        for r in researchers:
            r_copy = dict(r)
            r_copy['last_update'] = parse_dt(r_copy.get('last_update'))
            await conn.execute(
                text('''
                INSERT INTO researcher (
                    id, name, lattes_id, lattes_10_id, last_update, has_image, 
                    citations, orcid, abstract, abstract_en, abstract_ai, 
                    other_information, qtt_publications, institution_id
                ) VALUES (
                    :id, :name, :lattes_id, :lattes_10_id, :last_update, :has_image,
                    :citations, :orcid, :abstract, :abstract_en, :abstract_ai,
                    :other_information, :qtt_publications, :institution_id
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                r_copy,
            )

        # 3. Search Document Researcher (com embeddings)
        sdr_list = data.get('search_document_researcher', [])
        print(f'Inserindo {len(sdr_list)} documentos de pesquisadores...')
        for sdr in sdr_list:
            emb_str = str(sdr['embedding']) if sdr.get('embedding') else None
            await conn.execute(
                text('''
                INSERT INTO search_document_researcher (id, researcher_id, document_content, embedding, last_indexed_at)
                VALUES (:id, :researcher_id, :document_content, (:embedding)::vector, :last_indexed_at)
                ON CONFLICT (id) DO NOTHING;
            '''),
                {
                    'id': sdr['id'],
                    'researcher_id': sdr['researcher_id'],
                    'document_content': sdr['document_content'],
                    'embedding': emb_str,
                    'last_indexed_at': parse_dt(sdr.get('last_indexed_at')),
                },
            )

        # 4. Bibliographic Productions
        bps = data.get('bibliographic_production', [])
        print(f'Inserindo {len(bps)} produções bibliográficas...')
        for bp in bps:
            await conn.execute(
                text('''
                INSERT INTO bibliographic_production (
                    id, title, type, title_en, doi, nature, year, language, 
                    means_divulgation, homepage, relevance, has_image, 
                    scientific_divulgation, researcher_id, authors, year_, is_new
                ) VALUES (
                    :id, :title, :type, :title_en, :doi, :nature, :year, :language,
                    :means_divulgation, :homepage, :relevance, :has_image,
                    :scientific_divulgation, :researcher_id, :authors, :year_, :is_new
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                bp,
            )

        # 4.1 Periódicos
        mags = data.get('periodical_magazine', [])
        print(f'Inserindo {len(mags)} periódicos...')
        for mag in mags:
            await conn.execute(
                text('''
                INSERT INTO periodical_magazine (
                    id, name, issn, qualis, jcr, jcr_link, reference_period
                ) VALUES (
                    :id, :name, :issn, :qualis, :jcr, :jcr_link, :reference_period
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                mag,
            )

        # 4.2 Artigos
        arts = data.get('bibliographic_production_article', [])
        print(f'Inserindo {len(arts)} detalhes de artigos...')
        for art in arts:
            await conn.execute(
                text('''
                INSERT INTO bibliographic_production_article (
                    id, bibliographic_production_id, periodical_magazine_id, periodical_magazine_name, 
                    issn, qualis, jcr, jcr_link, stars, quadrennial
                ) VALUES (
                    :id, :bibliographic_production_id, :periodical_magazine_id, :periodical_magazine_name,
                    :issn, :qualis, :jcr, :jcr_link, :stars, :quadrennial
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                art,
            )

        # 4.2 Livros
        bks = data.get('bibliographic_production_book', [])
        print(f'Inserindo {len(bks)} detalhes de livros...')
        for bk in bks:
            await conn.execute(
                text('''
                INSERT INTO bibliographic_production_book (
                    id, bibliographic_production_id, isbn, qtt_volume, qtt_pages, 
                    publishing_company, publishing_company_city, stars
                ) VALUES (
                    :id, :bibliographic_production_id, :isbn, :qtt_volume, :qtt_pages,
                    :publishing_company, :publishing_company_city, :stars
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                bk,
            )

        # 4.3 Capítulos
        chps = data.get('bibliographic_production_book_chapter', [])
        print(f'Inserindo {len(chps)} detalhes de capítulos...')
        for chp in chps:
            await conn.execute(
                text('''
                INSERT INTO bibliographic_production_book_chapter (
                    id, bibliographic_production_id, book_title, isbn, organizers, 
                    publishing_company, publishing_company_city, stars
                ) VALUES (
                    :id, :bibliographic_production_id, :book_title, :isbn, :organizers,
                    :publishing_company, :publishing_company_city, :stars
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                chp,
            )

        # 5. Patentes
        pats = data.get('patent', [])
        print(f'Inserindo {len(pats)} patentes...')
        for pat in pats:
            pat_copy = dict(pat)
            if pat_copy.get('grant_date'):
                pat_copy['grant_date'] = parse_dt(pat_copy['grant_date'])
            await conn.execute(
                text('''
                INSERT INTO patent (
                    id, title, category, relevance, has_image, development_year, 
                    details, researcher_id, code, grant_date, deposit_date, is_new, stars
                ) VALUES (
                    :id, :title, :category, :relevance, :has_image, :development_year,
                    :details, :researcher_id, :code, :grant_date, :deposit_date, :is_new, :stars
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                pat_copy,
            )

        # 6. Softwares
        softs = data.get('software', [])
        print(f'Inserindo {len(softs)} softwares...')
        for soft in softs:
            await conn.execute(
                text('''
                INSERT INTO software (
                    id, title, platform, goal, relevance, has_image, environment, 
                    availability, researcher_id, year, is_new, stars, code
                ) VALUES (
                    :id, :title, :platform, :goal, :relevance, :has_image, :environment,
                    :availability, :researcher_id, :year, :is_new, :stars, :code
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                soft,
            )

        # 7. Relatórios Técnicos
        reps = data.get('research_report', [])
        print(f'Inserindo {len(reps)} relatórios técnicos...')
        for rep in reps:
            await conn.execute(
                text('''
                INSERT INTO research_report (
                    id, researcher_id, title, project_name, year, is_new, stars
                ) VALUES (
                    :id, :researcher_id, :title, :project_name, :year, :is_new, :stars
                ) ON CONFLICT (id) DO NOTHING;
            '''),
                rep,
            )

        # 8. Search Document Production (com embeddings)
        sdps = data.get('search_document_production', [])
        print(f'Inserindo {len(sdps)} documentos de produções com embeddings...')
        for sdp in sdps:
            emb_str = str(sdp['embedding']) if sdp.get('embedding') else None
            await conn.execute(
                text('''
                INSERT INTO search_document_production (id, production_id, type, document_content, embedding, last_indexed_at)
                VALUES (:id, :production_id, :type, :document_content, (:embedding)::vector, :last_indexed_at)
                ON CONFLICT (id) DO NOTHING;
            '''),
                {
                    'id': sdp['id'],
                    'production_id': sdp['production_id'],
                    'type': sdp['type'],
                    'document_content': sdp['document_content'],
                    'embedding': emb_str,
                    'last_indexed_at': parse_dt(sdp.get('last_indexed_at')),
                },
            )

    await engine.dispose()
    print('✅ Base populada e anexada com sucesso!')


def parse_args():
    parser = argparse.ArgumentParser(
        description='Popular/anexar Golden Dataset no PostgreSQL com pgvector'
    )
    parser.add_argument(
        '--db-url',
        type=str,
        default=os.getenv(
            'DATABASE_URL',
            'postgresql+asyncpg://postgres:postgres@localhost:5433/simcc',
        ),
        help='URL do banco de dados (padrão: DATABASE_URL ou localhost:5433/simcc)',
    )
    parser.add_argument(
        '--fixture-path',
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help='Caminho do arquivo JSON ou JSON.GZ da amostra',
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    await seed_golden_dataset(args.db_url, fixture_path=args.fixture_path)


if __name__ == '__main__':
    asyncio.run(main())
