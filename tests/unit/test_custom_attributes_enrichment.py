from unittest.mock import AsyncMock

import pytest

from simcc.repositories import researcher_repo
from simcc.services import researcher_service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enrich_researchers_with_institution_affiliation(monkeypatch):
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

    async def mock_list_inst(session, ids):
        return [
            {
                'id': 'd8091801-1402-4db6-9e8c-550f75727196',
                'workload': 40.0,
                'identity_territory': 'PORTAL DO SERTAO',
                'city_id': '87c2aa5b-c2e7-4959-99fc-77b385806c9e',
                'city_name': 'CACHOEIRA',
            }
        ]

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
        mock_list_inst,
    )

    researchers = [
        {
            'id': 'd8091801-1402-4db6-9e8c-550f75727196',
            'lattes_id': '8343393957854863',
            'name': 'ADRIANO ANUNCIACAO OLIVEIRA',
            'university': 'UFRB',
        },
        {
            'id': 'a1091801-1402-4db6-9e8c-550f75727199',
            'lattes_id': '4198535318645664',
            'name': 'ALBANY MENDONCA SILVA',
        },
    ]

    expected_len = 2
    enriched = await researcher_service.enrich_researchers(
        session, researchers
    )
    assert len(enriched) == expected_len

    # Primeiro pesquisador com dados institucionais
    expected_workload = 40.0
    r1 = enriched[0]
    assert r1['institution'] is not None
    assert r1['institution']['acronym'] == 'UFRB'
    assert r1['institution']['workload'] == expected_workload
    assert r1['institution']['identity_territory'] == 'PORTAL DO SERTAO'
    assert (
        r1['institution']['city_id'] == '87c2aa5b-c2e7-4959-99fc-77b385806c9e'
    )
    assert r1['institution']['city'] == 'CACHOEIRA'

    # Segundo pesquisador sem dados institucionais
    r2 = enriched[1]
    assert r2['institution'] is None
