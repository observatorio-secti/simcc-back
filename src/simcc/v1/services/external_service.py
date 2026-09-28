from typing import List

import nltk
import polars as pl
from nltk.corpus import stopwords

from simcc.v1.repositories import external_repo

# Ensure stopwords are available
try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords')


async def list_article_production(
    session, program_id=None, dep_id=None, year=2020
) -> List[dict]:
    article_production = await external_repo.list_article_production(
        session, program_id, dep_id, year
    )
    if not article_production:
        return []

    df = pl.DataFrame(article_production)

    # pivot handles grouping and counting qualis
    article_production_pivot = df.pivot(
        on='qualis',
        index=['name', 'year'],
        values='among',
        aggregate_function='sum',
    ).fill_null(0)

    # Citations are already SUMmed in SQL, but we need to group them if multiple qualis exist for same name/year
    citations = df.group_by(['name', 'year']).agg(pl.col('citations').sum())

    article_production_pivot = article_production_pivot.join(
        citations, on=['name', 'year'], how='left'
    )

    # Ensure all qualis columns exist and match schema
    for q in ['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4', 'C', 'SQ']:
        if q not in article_production_pivot.columns:
            article_production_pivot = article_production_pivot.with_columns(
                pl.lit(0).alias(q)
            )

    # Normalize column names to lowercase for schema compatibility
    article_production_pivot = article_production_pivot.rename({
        c: c.lower() for c in article_production_pivot.columns
    })

    return article_production_pivot.to_dicts()


async def get_departament(session, dep_id=None):
    return await external_repo.get_departament(session, dep_id)


async def get_docentes(session, filters):
    return await external_repo.get_docentes(session, filters)


async def get_researcher_data(session, cpf=None, name=None):
    return await external_repo.get_researcher_data(session, cpf, name)


async def get_technician(session):
    return await external_repo.get_technician(session)


async def get_departament_rt(session):
    return await external_repo.get_departament_rt(session)


async def list_words(session, term: str) -> List[dict]:
    stop_words = stopwords.words('english') + stopwords.words('portuguese')
    return await external_repo.list_words(session, term, stop_words)


async def post_congregation(session, file):
    # Process Excel file
    df = pl.read_excel(file.file, read_options={'header_row': 2})
    # Basic cleaning
    df = df.filter(~pl.all_horizontal(pl.all().is_null()))

    # Map DataFrame columns to expected repository format
    congregation_data = []
    for row in df.to_dicts():
        congregation_data.append({
            'MEMBRO': row.get('MEMBRO'),
            'DEPARTAMENTO': row.get('DEPARTAMENTO'),
            'MANDATO': row.get('MANDATO'),
            'EMAIL': row.get('E-MAIL'),
            'TELEFONE': row.get('TELEFONE'),
        })

    await external_repo.post_congregation(session, congregation_data)
    await session.commit()
