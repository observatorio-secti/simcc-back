from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import ProgrammingError

from simcc.v1.repositories import external_repo, powerBi_repo, researcher_repo
from simcc.v1.services import researcher_service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_departments_by_ids_fallback_on_db_error():
    session = AsyncMock()
    session.execute.side_effect = ProgrammingError(
        'relation ufmg.departament_researcher does not exist',
        params={},
        orig=Exception(),
    )
    result = await researcher_repo.list_departments_by_ids(
        session, ['d8091801-1402-4db6-9e8c-550f75727196']
    )
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_ufmg_data_by_ids_fallback_on_db_error():
    session = AsyncMock()
    session.execute.side_effect = ProgrammingError(
        'relation ufmg.researcher does not exist',
        params={},
        orig=Exception(),
    )
    result = await researcher_repo.list_ufmg_data_by_ids(
        session, ['d8091801-1402-4db6-9e8c-550f75727196']
    )
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_user_data_by_lattes_ids_fallback_on_db_error():
    session = AsyncMock()
    session.execute.side_effect = ProgrammingError(
        'relation admin.users does not exist',
        params={},
        orig=Exception(),
    )
    result = await researcher_repo.list_user_data_by_lattes_ids(
        session, ['1234567890123456']
    )
    assert result == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_departament_rt_fallback_on_db_error():
    session = AsyncMock()
    session.execute.side_effect = ProgrammingError(
        'relation ufmg.researcher does not exist',
        params={},
        orig=Exception(),
    )
    result = await researcher_repo.get_departament_rt(session)
    assert result == {'teachers': [], 'technician': []}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enrich_researchers_with_fallback_data(monkeypatch):
    session = AsyncMock()

    async def mock_list_gp(session, ids):
        return []

    async def mock_list_rg(session, ids):
        return []

    async def mock_list_subsidy(session, ids):
        return []

    async def mock_list_dep(session, ids):
        return []

    async def mock_list_ufmg(session, ids):
        return []

    async def mock_list_user(session, ids):
        return []

    async def mock_list_institution(session, ids):
        return []

    monkeypatch.setattr(
        researcher_repo, 'list_graduate_programs_by_ids', mock_list_gp
    )
    monkeypatch.setattr(
        researcher_repo, 'list_research_groups_by_ids', mock_list_rg
    )
    monkeypatch.setattr(
        researcher_repo, 'list_subsidy_by_ids', mock_list_subsidy
    )
    monkeypatch.setattr(
        researcher_repo, 'list_departments_by_ids', mock_list_dep
    )
    monkeypatch.setattr(
        researcher_repo, 'list_ufmg_data_by_ids', mock_list_ufmg
    )
    monkeypatch.setattr(
        researcher_repo, 'list_user_data_by_lattes_ids', mock_list_user
    )
    monkeypatch.setattr(
        researcher_repo,
        'list_institution_data_by_researcher_ids',
        mock_list_institution,
    )

    researchers = [
        {
            'id': 'd8091801-1402-4db6-9e8c-550f75727196',
            'lattes_id': '8343393957854863',
            'name': 'ADRIANO ANUNCIACAO OLIVEIRA',
        }
    ]

    enriched = await researcher_service.enrich_researchers(
        session, researchers
    )
    assert len(enriched) == 1
    assert enriched[0]['departments'] == []
    assert enriched[0]['ufmg'] is None
    assert enriched[0]['user'] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_external_repo_fallbacks_on_db_error():
    session = AsyncMock()
    session.execute.side_effect = ProgrammingError(
        'relation does not exist',
        params={},
        orig=Exception(),
    )

    assert await external_repo.get_departament(session) == []
    assert await external_repo.get_docentes(session, None) == []
    assert await external_repo.get_researcher_data(session) == []
    assert await external_repo.get_technician(session) == []
    assert await external_repo.list_article_production(session) == []
    assert await external_repo.list_words(session, 'test', []) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_powerbi_repo_fallbacks_on_db_error():
    session = AsyncMock()
    session.execute.side_effect = ProgrammingError(
        'relation does not exist',
        params={},
        orig=Exception(),
    )

    assert await powerBi_repo.get_dim_departament_technician(session) == []
    assert await powerBi_repo.get_dim_departament_researcher(session) == []
    assert await powerBi_repo.get_guidance(session) == []
    assert await powerBi_repo.get_dim_tags(session) == []
    assert await powerBi_repo.get_ind_guidance_ori(session) == []
    assert await powerBi_repo.get_fat_guidance_history(session) == []
