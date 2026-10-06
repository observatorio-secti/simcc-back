from uuid import UUID

import pandas as pd
from numpy import nan

from simcc.repositories.admin import collection_repository
from simcc.repositories.simcc import (
    institution_repository,
    researcher_repository,
)
from simcc.schemas.Researcher import CoAuthorship


async def filter_star_entrys(conn, type, user):
    ids_dict = await collection_repository.filter_star_entrys(
        conn, type, user['user_id']
    )
    return ids_dict.get('ids') if ids_dict else None


async def merge_researcher_data(researchers: pd.DataFrame, conn) -> pd.DataFrame:
    gp = await researcher_repository.list_graduate_programs(conn)
    rg = await researcher_repository.list_research_groups(conn)
    subsidy = await researcher_repository.list_foment_data(conn)
    dep = await researcher_repository.list_departament_data(conn)

    sources = {
        'graduate_programs': gp,
        'research_groups': rg,
        'subsidy': subsidy,
        'departments': dep,
    }

    for column, source in sources.items():
        if source:
            dataframe = pd.DataFrame(source)
            researchers = researchers.merge(dataframe, on='id', how='left')
        else:
            researchers[column] = None

    ufmg_data = await researcher_repository.list_ufmg_data(conn)
    if ufmg_data:
        ufmg_df = pd.DataFrame(ufmg_data)[['id']]
        ufmg_df['ufmg'] = ufmg_data
        researchers = researchers.merge(ufmg_df, on='id', how='left')
    else:
        researchers['ufmg'] = None
    user_data = await researcher_repository.list_user_data(conn)
    if user_data:
        user_df = pd.DataFrame(user_data)[['lattes_id', 'user']]
        researchers = researchers.merge(user_df, on='lattes_id', how='left')
    else:
        researchers['user'] = None

    return researchers


async def get_researcher_filter(conn):
    return await researcher_repository.get_researcher_filter(conn)


async def search_in_area_specialty(conn, conn_admin, filters):
    if filters.star:
        filters.star = await filter_star_entrys(
            conn_admin, 'RESEARCHER', filters.star
        )
    researchers = await researcher_repository.search_in_area_specialty(
        conn, filters
    )
    if not researchers:
        return []

    researchers = pd.DataFrame(researchers)
    researchers = await merge_researcher_data(researchers, conn)

    researchers = researchers.replace(nan, '')
    return researchers.to_dict(orient='records')


async def search_in_participation_event(conn, conn_admin, filters):
    if filters.star:
        filters.star = await filter_star_entrys(
            conn_admin, 'RESEARCHER', filters.star
        )
    researchers = await researcher_repository.search_in_participation_event(
        conn, filters
    )

    if not researchers:
        return []

    researchers = pd.DataFrame(researchers)
    researchers = await merge_researcher_data(researchers, conn)

    researchers = researchers.replace(nan, '')
    return researchers.to_dict(orient='records')


async def search_in_bibliographic_production(conn, conn_admin, filters, type):
    if filters.star:
        filters.star = await filter_star_entrys(
            conn_admin, 'RESEARCHER', filters.star
        )
    researchers = await researcher_repository.search_in_bibliographic_production(
        conn, filters, type
    )
    if not researchers:
        return []

    researchers = pd.DataFrame(researchers)
    researchers = await merge_researcher_data(researchers, conn)

    researchers = researchers.replace(nan, '')
    return researchers.to_dict(orient='records')


async def search_in_articles(conn, default_filters):
    researchers = await researcher_repository.search_in_articles(
        conn, default_filters
    )
    if not researchers:
        return []

    researchers = pd.DataFrame(researchers)
    researchers = await merge_researcher_data(researchers, conn)

    researchers = researchers.replace(nan, '')
    return researchers.to_dict(orient='records')


async def search_in_researcher(conn, conn_admin, filters, name):
    if filters.star:
        filters.star = await filter_star_entrys(
            conn_admin, 'RESEARCHER', filters.star
        )
    researchers = await researcher_repository.search_in_researcher(
        conn, filters, name
    )
    if not researchers:
        return []

    researchers = pd.DataFrame(researchers)
    researchers = await merge_researcher_data(researchers, conn)

    researchers = researchers.replace(nan, '')
    return researchers.to_dict(orient='records')


async def list_outstanding_researchers(conn, filters):
    researchers = await researcher_repository.search_in_researcher(
        conn, filters, None
    )
    if not researchers:
        return []

    researchers = pd.DataFrame(researchers)
    researchers = await merge_researcher_data(researchers, conn)

    researchers = researchers.replace(nan, '')
    return researchers.to_dict(orient='records')


async def serch_in_name(conn, default_filters, name):
    researchers = await researcher_repository.search_in_name(
        conn, default_filters, name
    )
    if not researchers:
        return []

    researchers = pd.DataFrame(researchers)
    researchers = await merge_researcher_data(researchers, conn)

    researchers = researchers.replace(nan, '')
    return researchers.to_dict(orient='records')


def list_co_authorship(researcher_id: UUID) -> list[CoAuthorship]:
    co_authorship = researcher_repository.list_co_authorship(researcher_id)

    if not co_authorship:
        return []

    co_authorship = pd.DataFrame(co_authorship)
    institution = institution_repository.get_institution(
        researcher_id=researcher_id
    )
    researcher = researcher_repository.get_researcher(researcher_id)

    def co_authorship_type(co_authorship_institution):
        if co_authorship_institution == institution['name']:
            return 'internal'
        return 'external'

    co_authorship['type'] = co_authorship['institution'].apply(
        co_authorship_type
    )
    co_authorship['initials'] = (
        co_authorship['name']
        .str.replace('.', '', regex=True)
        .str.split()
        .apply(lambda x: ''.join(word[0] for word in x))
    )

    agg_config = {
        'among': 'sum',
        'type': lambda x: 'internal' if 'internal' in x.values else 'external',
    }
    columns = ['name', 'initials']
    co_authorship = co_authorship.groupby(columns).agg(agg_config).reset_index()
    co_authorship = co_authorship[co_authorship['name'] != researcher['name']]
    return co_authorship.to_dict(orient='records')


async def search_in_patents(conn, conn_admin, filters):
    if filters.star:
        filters.star = await filter_star_entrys(
            conn_admin, 'RESEARCHER', filters.star
        )
    researchers = await researcher_repository.search_in_patents(conn, filters)
    if not researchers:
        return []

    researchers = pd.DataFrame(researchers)
    researchers = await merge_researcher_data(researchers, conn)

    researchers = researchers.replace(nan, '')
    return researchers.to_dict(orient='records')


async def get_academic_degree(conn, default_filters):
    return await researcher_repository.academic_degree(conn, default_filters)


async def get_great_area(conn, default_filters):
    return await researcher_repository.get_great_area(conn, default_filters)


async def get_labs(conn, lattes_id, researcher_id):
    return await researcher_repository.get_labs(conn, lattes_id, researcher_id)


def _get_current_quadrienal(year_start: int | None = None, year_end: int | None = None) -> tuple[int, int]:
    """
    Retorna o intervalo de anos para o relatório de situação.
    Por padrão, utiliza o quadriênio avaliativo de referência da CAPES (2021-2024).
    """
    if year_start is not None and year_end is not None:
        return year_start, year_end
    # Padrão da pós-graduação e avaliação CAPES atual nos painéis do iaPós
    return 2021, 2024


async def get_situation_report(
    conn,
    researcher_id: str,
    year_start: int | None = None,
    year_end: int | None = None,
) -> dict:
    """
    Consolida os dados para o Relatório de Situação do Pesquisador:
    - Dados cadastrais e programas de pós-graduação
    - Orientações ativas (em andamento)
    - Produção bibliográfica na quadrienal de referência
    """
    start_year, end_year = _get_current_quadrienal(year_start, year_end)

    researcher = await researcher_repository.get_situation_report_researcher(
        conn, researcher_id
    )
    if not researcher:
        return {}

    active_guidances = await researcher_repository.get_situation_report_active_guidances(
        conn, researcher_id
    )

    quadrienal_articles = await researcher_repository.get_situation_report_quadrienal_articles(
        conn, researcher_id, start_year, end_year
    )

    quadrienal_summary = await researcher_repository.get_situation_report_quadrienal_summary(
        conn, researcher_id, start_year, end_year
    )

    # Serializa dicts/UUIDs para JSON-safe
    def safe(row):
        return {k: (str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v)
                for k, v in dict(row).items()}

    return {
        'quadrienal': f'{start_year}-{end_year}',
        'researcher': safe(researcher),
        'active_guidances': [safe(g) for g in (active_guidances or [])],
        'quadrienal_articles': [safe(a) for a in (quadrienal_articles or [])],
        'quadrienal_summary': [safe(s) for s in (quadrienal_summary or [])],
    }
