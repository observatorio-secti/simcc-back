"""Filtros modulares para a consulta de pesquisadores v2 sobre MVs.

Convenção para novos filtros:
1. Adicionar o campo em `ResearcherFilter` (schemas/filters.py), com
   `Field(description=...)`. Ele vira parâmetro de query automaticamente.
2. Criar `_by_<nome>(filters) -> ColumnElement[bool] | None` neste módulo.
3. Registrar a função em `_FILTER_BUILDERS`.
4. Adicionar testes em `tests/v2/unit/test_researcher_filters.py`.

Diretrizes de arquitetura:
- Filtros sobre a MV usam índices GIN de array (`&&` / overlap) ou
  igualdade em colunas escalares.
- Filtros sobre obras (`q`, anos, `source_type`) passam por
  `document_conditions`, a única definição de "obra que conta" usada pela
  busca, pela relevância, pelas evidências e pelos facets.
- O faceting disjuntivo usa `exclude` em `build_researcher_conditions`:
  os campos excluídos são zerados no filtro antes de gerar as condições.
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

from simcc.core.db.models.expertise import GreatAreaExpertise
from simcc.core.db.models.production import Foment
from simcc.core.db.models.researcher import ResearcherAreaExpertise
from simcc.v2.repositories.search_tables import (
    mv_researcher_search,
    mv_search_documents,
)
from simcc.v2.schemas.filters import ResearcherFilter

r = mv_researcher_search
d = mv_search_documents


def search_tsquery(filters: ResearcherFilter) -> Optional[ColumnElement]:
    """`tsquery` da busca textual, ou None sem `q`."""
    if not filters.q or not filters.q.strip():
        return None
    return func.websearch_to_tsquery('pt_unaccent', filters.q.strip())


def document_conditions(
    filters: ResearcherFilter,
) -> list[ColumnElement[bool]]:
    """Condições sobre `mv_search_documents` que definem as obras que contam:
    casam com `q` (se houver), estão no intervalo de anos e são dos tipos
    pedidos em `source_type`."""
    conds: list[ColumnElement[bool]] = []
    tsq = search_tsquery(filters)
    if tsq is not None:
        conds.append(d.c.search_vector.op('@@')(tsq))
    if filters.year_start is not None:
        conds.append(d.c.year_ >= filters.year_start)
    if filters.year_end is not None:
        conds.append(d.c.year_ <= filters.year_end)
    if filters.source_type:
        conds.append(d.c.source_type.in_(filters.source_type))
    return conds


def profile_counts(filters: ResearcherFilter) -> bool:
    """O perfil (nome e resumo) só conta quando a busca não foi restrita a
    tipos de obra."""
    return not filters.source_type


def _documents_exist(filters: ResearcherFilter) -> ColumnElement[bool]:
    return (
        select(literal_column('1'))
        .select_from(d)
        .where(
            d.c.researcher_id == r.c.researcher_id,
            *document_conditions(filters),
        )
        .exists()
    )


def _by_search_query(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    """Pesquisadores cujo perfil ou alguma obra casa com o termo."""
    tsq = search_tsquery(filters)
    if tsq is None:
        return None
    docs_match = _documents_exist(filters)
    if not profile_counts(filters):
        return docs_match
    return or_(r.c.profile_vector.op('@@')(tsq), docs_match)


def _by_source_type(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    """Sem `q`: exige ao menos uma obra dos tipos pedidos (no intervalo de
    anos, se houver). Com `q`, o tipo já é aplicado na busca textual."""
    if not filters.source_type or search_tsquery(filters) is not None:
        return None
    return _documents_exist(filters)


def _by_year_range(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    """Sem `q` e sem `source_type`: produção em algum ano do intervalo."""
    if search_tsquery(filters) is not None or filters.source_type:
        return None
    if filters.year_start is None and filters.year_end is None:
        return None

    current_year = datetime.now(timezone.utc).year + 5
    start = filters.year_start if filters.year_start is not None else 1950
    end = filters.year_end if filters.year_end is not None else current_year
    return r.c.production_years.overlap(list(range(start, end + 1)))


def _by_institutions(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    if not filters.institution_id:
        return None
    return r.c.institution_ids.overlap(filters.institution_id)


def _by_graduate_programs(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    if not filters.graduate_program_id:
        return None
    return r.c.graduate_program_ids.overlap(filters.graduate_program_id)


def _by_cities(filters: ResearcherFilter) -> Optional[ColumnElement[bool]]:
    if not filters.city_id:
        return None
    return r.c.city_ids.overlap(filters.city_id)


def _by_identity_territories(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    if not filters.identity_territory:
        return None
    return r.c.identity_territories.overlap(filters.identity_territory)


def _by_graduation(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    if not filters.graduation:
        return None
    return r.c.graduation.in_(filters.graduation)


def _by_classification(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    if not filters.classification:
        return None
    return r.c.classification.in_(filters.classification)


def _by_area(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    if not filters.area:
        return None
    rae = ResearcherAreaExpertise.__table__
    gae = GreatAreaExpertise.__table__
    normalized = [a.replace(' ', '_').upper() for a in filters.area]
    area_cond = or_(
        gae.c.name.in_(filters.area),
        func.upper(gae.c.name).in_(normalized),
    )
    return (
        select(literal_column('1'))
        .select_from(rae.join(gae, gae.c.id == rae.c.great_area_expertise_id))
        .where(
            rae.c.researcher_id == r.c.researcher_id,
            area_cond,
        )
        .exists()
    )


def _by_modality(
    filters: ResearcherFilter,
) -> Optional[ColumnElement[bool]]:
    if not filters.modality:
        return None
    f = Foment.__table__
    return (
        select(literal_column('1'))
        .select_from(f)
        .where(
            f.c.researcher_id == r.c.researcher_id,
            f.c.modality_name.in_(filters.modality),
        )
        .exists()
    )


_FILTER_BUILDERS: list[
    Callable[[ResearcherFilter], Optional[ColumnElement[bool]]]
] = [
    _by_search_query,
    _by_source_type,
    _by_year_range,
    _by_institutions,
    _by_graduate_programs,
    _by_cities,
    _by_identity_territories,
    _by_graduation,
    _by_classification,
    _by_area,
    _by_modality,
]


def without_fields(
    filters: ResearcherFilter, fields: frozenset[str]
) -> ResearcherFilter:
    """Cópia do filtro com os campos indicados de volta ao valor padrão."""
    if not fields:
        return filters
    return filters.model_copy(
        update={
            field: ResearcherFilter.model_fields[field].get_default(
                call_default_factory=True
            )
            for field in fields
        }
    )


def build_researcher_conditions(
    filters: ResearcherFilter,
    exclude: frozenset[str] = frozenset(),
) -> list[ColumnElement[bool]]:
    """Gera as condições ativas. `exclude` recebe nomes de campos de
    `ResearcherFilter` a ignorar (faceting disjuntivo)."""
    effective = without_fields(filters, exclude)
    return [
        cond
        for builder in _FILTER_BUILDERS
        if (cond := builder(effective)) is not None
    ]


def matching_researcher_ids(
    filters: ResearcherFilter,
    exclude: frozenset[str] = frozenset(),
):
    """Subconsulta com os ids dos pesquisadores que passam nos filtros."""
    stmt = select(r.c.researcher_id)
    conditions = build_researcher_conditions(filters, exclude)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    return stmt
