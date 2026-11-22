"""Referência geográfica compartilhada pelos repositórios v2.

Territórios de Identidade (código SEI 1 a 27) e municípios (código IBGE)
vêm de `identity_territory` e `municipality`, populadas pela rotina
`seed_geo_reference` do simcc-etl. Os filtros aceitam o código SEI ou, por
compatibilidade, o nome do território.
"""

from collections.abc import Iterable
from typing import Optional

from sqlalchemy import (
    ColumnElement,
    String,
    Text,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.graduate_program import GraduateProgram
from simcc.core.db.models.location import IdentityTerritory, Municipality

IT = IdentityTerritory
M = Municipality
GP = GraduateProgram

# Rótulo do grupo de itens sem território (municípios fora da BA)
NO_TERRITORY_LABEL = 'Sem território'


def _territory_match(values: Iterable[str]) -> ColumnElement[bool]:
    values = [v.strip() for v in values if v and v.strip()]
    return or_(
        cast(IT.code, String).in_(values),
        func.upper(IT.name).in_([v.upper() for v in values]),
    )


def territory_codes_array(values: list[str]):
    """Subconsulta escalar com o array de códigos que casam com `values`
    (código SEI ou nome). NULL quando nada casa, o que zera o `&&`."""
    return (
        select(func.array_agg(IT.code))
        .where(_territory_match(values))
        .scalar_subquery()
    )


def city_codes_array(values: list[str]):
    return cast([v.strip() for v in values if v.strip()], ARRAY(Text))


async def resolve_territory_codes(
    session: AsyncSession, values: list[str]
) -> list[int]:
    """Códigos SEI dos valores do filtro, na ordem da tabela."""
    if not values:
        return []
    rows = await session.execute(
        select(IT.code).where(_territory_match(values)).order_by(IT.code)
    )
    return [int(code) for code in rows.scalars()]


def _norm(column) -> ColumnElement:
    return func.f_unaccent(func.lower(func.trim(column)))


def gp_municipality_join() -> ColumnElement[bool]:
    """Condição que liga a sede do programa (`city` + `state`, texto) ao
    município do IBGE."""
    return (M.uf == GP.state) & (_norm(M.name) == _norm(GP.city))


def gp_ibge_code() -> ColumnElement:
    """Código IBGE da sede do programa (subconsulta correlacionada)."""
    return (
        select(M.ibge_code)
        .where(gp_municipality_join())
        .limit(1)
        .scalar_subquery()
    )


def gp_territory_code() -> ColumnElement:
    """Código SEI do território da sede do programa."""
    return (
        select(M.territory_code)
        .where(gp_municipality_join())
        .limit(1)
        .scalar_subquery()
    )


def gp_territory_condition(values: list[str]) -> Optional[ColumnElement]:
    if not values:
        return None
    return gp_territory_code().in_(
        select(IT.code).where(_territory_match(values))
    )


def gp_city_code_condition(values: list[str]) -> Optional[ColumnElement]:
    if not values:
        return None
    return gp_ibge_code().in_([v.strip() for v in values if v.strip()])
