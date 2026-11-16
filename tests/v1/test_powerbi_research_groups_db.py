import pytest
from unittest.mock import AsyncMock, MagicMock

from simcc.v1.queries.powerBi_query import (
    DimResearchGroupQuery,
    FatGroupLeadersQuery,
)
from simcc.v1.repositories.powerBi_repo import (
    get_dim_research_group,
    get_fat_group_leaders,
)


def test_fat_group_leaders_query_sql():
    session = MagicMock()
    query = FatGroupLeadersQuery(session)
    sql = query.build_sql()
    assert 'FROM research_group' in sql
    assert 'first_leader_id' in sql
    assert 'second_leader_id' in sql
    assert 'group_identifier' in sql


def test_dim_research_group_query_sql():
    session = MagicMock()
    query = DimResearchGroupQuery(session)
    sql = query.build_sql()
    assert 'FROM public.research_group rg' in sql
    assert 'RIGHT JOIN institution i' in sql


@pytest.mark.asyncio
async def test_repo_get_fat_group_leaders():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {
            'id': 'group-1',
            'name': 'Grupo Teste',
            'first_leader': 'Líder 1',
            'first_leader_id': 'res-1',
            'second_leader': None,
            'second_leader_id': None,
            'AREA': 'Computação',
            'YEAR': '2021',
        }
    ]
    mock_session.execute.return_value = mock_result

    data = await get_fat_group_leaders(mock_session)
    assert len(data) == 1
    assert data[0]['name'] == 'Grupo Teste'


@pytest.mark.asyncio
async def test_repo_get_dim_research_group():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {
            'group_id': 'group-1',
            'group_name': 'Grupo Teste',
            'area': 'Computação',
            'institution_id': 'inst-1',
        }
    ]
    mock_session.execute.return_value = mock_result

    data = await get_dim_research_group(mock_session)
    assert len(data) == 1
    assert data[0]['group_name'] == 'Grupo Teste'


if __name__ == '__main__':
    import asyncio
    test_fat_group_leaders_query_sql()
    test_dim_research_group_query_sql()
    asyncio.run(test_repo_get_fat_group_leaders())
    asyncio.run(test_repo_get_dim_research_group())
    print('All powerbi research group tests passed!')
