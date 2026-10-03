"""Repositório para sugestão de termos a partir do dicionário de pesquisa."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.miscellaneous import ResearchDictionary
from simcc.v2.schemas.suggestion import Suggestion

# Maior code point Unicode: limite superior do intervalo de um prefixo
PREFIX_UPPER_BOUND = '\U0010ffff'


async def fetch_suggestions(
    session: AsyncSession,
    q: str,
    source_types: list[str],
    limit: int,
) -> list[Suggestion]:
    """Termos do dicionário que começam com `q`, por frequência.

    O prefixo é comparado como intervalo (`~>=~` / `~<~`) sobre a mesma
    expressão do índice `idx_research_dictionary_term_prefix`, o que
    mantém a busca indexada mesmo em planos genéricos.
    """
    normalized_term = func.f_unaccent(func.lower(ResearchDictionary.term))
    prefix = func.f_unaccent(func.lower(q))
    upper_bound = func.f_unaccent(func.lower(q + PREFIX_UPPER_BOUND))
    frequency = func.sum(ResearchDictionary.frequency).label('frequency')
    source_types_col = func.array_remove(
        func.array_agg(ResearchDictionary.type_.distinct()),
        None,
    ).label('source_types')

    stmt = (
        select(ResearchDictionary.term, frequency, source_types_col)
        .where(
            normalized_term.op('~>=~')(prefix),
            normalized_term.op('~<~')(upper_bound),
        )
        .group_by(ResearchDictionary.term)
        .order_by(frequency.desc(), ResearchDictionary.term.asc())
        .limit(limit)
    )
    if source_types:
        stmt = stmt.where(ResearchDictionary.type_.in_(source_types))

    rows = (await session.execute(stmt)).mappings().all()
    return [
        Suggestion(
            term=row['term'],
            frequency=row['frequency'],
            source_types=sorted([t for t in (row['source_types'] or []) if t]),
        )
        for row in rows
    ]
