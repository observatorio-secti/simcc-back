from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from simcc.v1.repositories import researcher_repo
from simcc.v1.services import researcher_service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_institutions_enrichment(monkeypatch):
    session = AsyncMock()
    inst_id_1 = uuid4()
    inst_id_2 = uuid4()

    mock_data = [
        {
            'id': inst_id_1,
            'name': 'Universidade Federal da Bahia',
            'acronym': 'UFBA',
            'count_r': 100,
            'count_gp': 10,
            'count_gpr': 20,
            'count_gps': 30,
            'count_d': 0,
            'count_t': 0,
            'researchers': [],
        },
        {
            'id': inst_id_2,
            'name': 'Instituição Sem Imagens',
            'acronym': 'OUTRA',
            'count_r': 5,
            'count_gp': 1,
            'count_gpr': 1,
            'count_gps': 1,
            'count_d': 0,
            'count_t': 0,
            'researchers': [],
        },
    ]

    async def mock_list_institutions(session):
        return mock_data

    monkeypatch.setattr(
        researcher_repo, 'list_institutions', mock_list_institutions
    )

    result = await researcher_service.list_institutions(session)
    assert len(result) == 2

    # UFBA deve ter image e cover resolvidos do storage
    ufba = result[0]
    assert ufba['acronym'] == 'UFBA'
    assert ufba['image'] == '/storage/institutions/picture/UFBA.png'
    assert ufba['cover'] == '/storage/institutions/covers/UFBA.jpg'

    # OUTRA não possui imagens no storage
    outra = result[1]
    assert outra['acronym'] == 'OUTRA'
    assert outra['image'] is None
    assert outra['cover'] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_institution_enrichment(monkeypatch):
    session = AsyncMock()
    inst_id = uuid4()

    mock_data = {
        'id': inst_id,
        'name': 'Universidade Estadual de Feira de Santana',
        'acronym': 'UEFS',
        'count_r': 50,
        'count_gp': 5,
        'count_gpr': 10,
        'count_gps': 15,
        'count_d': 0,
        'count_t': 0,
        'researchers': [],
    }

    async def mock_get_institution(session, institution_id):
        return mock_data

    monkeypatch.setattr(
        researcher_repo, 'get_institution', mock_get_institution
    )

    result = await researcher_service.get_institution(session, inst_id)
    assert result is not None
    assert result['id'] == inst_id
    assert result['acronym'] == 'UEFS'
    assert result['image'] == '/storage/institutions/picture/UEFS.png'
    assert result['cover'] == '/storage/institutions/covers/UEFS.jpg'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enrich_researchers_with_institution_object(monkeypatch):
    session = AsyncMock()
    inst_id = uuid4()
    researcher_id = uuid4()

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
        return []

    async def mock_list_institutions_by_ids(session, ids):
        return [
            {
                'id': inst_id,
                'name': 'Universidade Federal da Bahia',
                'acronym': 'UFBA',
                'image': None,
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
    monkeypatch.setattr(
        researcher_repo,
        'list_institutions_by_ids',
        mock_list_institutions_by_ids,
    )

    researchers = [
        {
            'id': researcher_id,
            'lattes_id': '1234567890123456',
            'lattes_10_id': '1234567890',
            'name': 'Pesquisador UFBA',
            'institution_id': inst_id,
            'university': 'Universidade Federal da Bahia',
        },
        {
            'id': uuid4(),
            'lattes_id': '9999999999999999',
            'lattes_10_id': '9999999999',
            'name': 'Pesquisador Sem Instituição',
            'institution_id': None,
            'university': None,
        },
    ]

    enriched = await researcher_service.enrich_researchers(
        session, researchers
    )
    assert len(enriched) == 2

    # Pesquisador 1: deve possuir o objeto institution completo
    r1 = enriched[0]
    assert r1['institution'] is not None
    assert r1['institution']['id'] == inst_id
    assert r1['institution']['name'] == 'Universidade Federal da Bahia'
    assert r1['institution']['acronym'] == 'UFBA'
    assert (
        r1['institution']['image'] == '/storage/institutions/picture/UFBA.png'
    )
    assert (
        r1['institution']['cover'] == '/storage/institutions/covers/UFBA.jpg'
    )
    assert r1['image_university'] == '/storage/institutions/picture/UFBA.png'

    # Pesquisador 2: sem instituição
    r2 = enriched[1]
    assert r2['institution'] is None
