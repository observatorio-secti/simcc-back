"""Filtros modulares para a consulta de pesquisadores v2 sobre MVs.

Convenção para novos filtros:
1. Adicionar o campo correspondente em `ResearcherFilter` (com
   documentação `Field(description=...)`).
2. Criar a função `_by_<nome>(filters: ResearcherFilter)` retornando
   `ColumnElement[bool] | None` neste módulo.
3. Registrar a função no dicionário `_FILTER_BUILDERS`.
4. Adicionar testes em `tests/v2/unit/test_researcher_filters.py`.

Diretrizes de arquitetura:
- Filtros baseados em visões materializadas usam índices GIN de array
  (`&&` / overlap) e busca textual `tsquery` com operador `@@`.
- A busca textual combina match em `profile_vector` na Camada 2
  (`mv_researcher_search`) com semi-join (`EXISTS`) na Camada 1
  (`mv_search_documents`).
- O faceting disjuntivo utiliza o parâmetro `exclude` em
  `build_researcher_conditions`, ignorando o filtro do próprio campo.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    ColumnElement,
    and_,
    func,
    literal_column,
    or_,
    select,
)

from simcc.v2.repositories.search_tables import (
    mv_researcher_search,
    mv_search_documents,
)
from simcc.v2.schemas.filters import ResearcherFilter


def _by_search_query(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    """Filtra pesquisadores por termo textual em perfil ou documentos."""
    if not filters.q or not filters.q.strip():
        return None

    clean_q = filters.q.strip()
    tsq = func.websearch_to_tsquery('pt_unaccent', clean_q)

    # Condições no documento (Camada 1)
    doc_conds: list[ColumnElement[bool]] = [
        mv_search_documents.c.researcher_id
        == mv_researcher_search.c.researcher_id,
        mv_search_documents.c.search_vector.op('@@')(tsq),
    ]

    # Quando q está presente, o intervalo de ano restringe as obras que casam
    if filters.year_start is not None:
        doc_conds.append(mv_search_documents.c.year_ >= filters.year_start)
    if filters.year_end is not None:
        doc_conds.append(mv_search_documents.c.year_ <= filters.year_end)

    doc_exists = (
        select(literal_column('1'))
        .select_from(mv_search_documents)
        .where(and_(*doc_conds))
        .exists()
    )

    profile_match = mv_researcher_search.c.profile_vector.op('@@')(tsq)
    return or_(profile_match, doc_exists)


def _by_institutions(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    """Filtra pesquisadores vinculados a qualquer uma das instituições."""
    if filters.institution_id:
        return mv_researcher_search.c.institution_ids.overlap(
            filters.institution_id
        )
    return None


def _by_graduate_programs(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    """Filtra pesquisadores associados a qualquer um dos programas."""
    if filters.graduate_program_id:
        return mv_researcher_search.c.graduate_program_ids.overlap(
            filters.graduate_program_id
        )
    return None


def _by_year_range(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    """Filtra pesquisadores com produções no intervalo (quando sem q)."""
    # Quando q está presente, o filtro de ano é aplicado nas obras que casam
    if filters.q and filters.q.strip():
        return None

    if filters.year_start is not None or filters.year_end is not None:
        current_year = datetime.now(timezone.utc).year + 5
        start = filters.year_start if filters.year_start is not None else 1950
        end = (
            filters.year_end if filters.year_end is not None else current_year
        )
        years = list(range(start, end + 1))
        return mv_researcher_search.c.production_years.overlap(years)

    return None


_FILTER_BUILDERS: dict[
    str, Callable[[ResearcherFilter], Optional[ColumnElement[bool]]]
] = {
    'q': _by_search_query,
    'institution_id': _by_institutions,
    'graduate_program_id': _by_graduate_programs,
    'year_range': _by_year_range,
}


def build_researcher_conditions(
    filters: ResearcherFilter,
    exclude: frozenset[str] = frozenset(),
) -> list[ColumnElement[bool]]:
    """Gera a lista de condições ativas, permitindo exclusão para faceting."""
    return [
        cond
        for key, builder in _FILTER_BUILDERS.items()
        if key not in exclude and (cond := builder(filters)) is not None
    ]
