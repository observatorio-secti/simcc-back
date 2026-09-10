from http import HTTPStatus
from uuid import uuid4

import pytest

from simcc.core.db.models.institution import Institution
from simcc.core.db.models.research_group import ResearchGroup
from simcc.core.db.models.researcher import Researcher


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_research_groups_by_institution_id_endpoint(
    session, async_client
):
    # 1. Cria duas instituições com acrônimos únicos
    acronym_1 = f'U{uuid4().hex[:6].upper()}'
    acronym_2 = f'U{uuid4().hex[:6].upper()}'

    inst_1 = Institution(
        name=f'Universidade {acronym_1}',
        acronym=acronym_1,
    )
    inst_2 = Institution(
        name=f'Universidade {acronym_2}',
        acronym=acronym_2,
    )
    session.add_all([inst_1, inst_2])
    await session.commit()
    await session.refresh(inst_1)
    await session.refresh(inst_2)

    # 2. Cria pesquisadores líderes para satisfazer o WHERE da query
    res_1 = Researcher(
        name=f'Lider {acronym_1}',
        lattes_id=str(uuid4().int)[:16],
        institution_id=inst_1.id,
    )
    res_2 = Researcher(
        name=f'Lider {acronym_2}',
        lattes_id=str(uuid4().int)[:16],
        institution_id=inst_2.id,
    )
    session.add_all([res_1, res_2])
    await session.commit()
    await session.refresh(res_1)
    await session.refresh(res_2)

    # 3. Cria grupos de pesquisa vinculados às instituições através do acrônimo
    rg_1 = ResearchGroup(
        name=f'Grupo Pesquisa {acronym_1}',
        institution=acronym_1,
        area='CIENCIAS EXATAS E DA TERRA',
        first_leader_id=res_1.id,
        first_leader=res_1.name,
    )
    rg_2 = ResearchGroup(
        name=f'Grupo Pesquisa {acronym_2}',
        institution=acronym_2,
        area='CIENCIAS BIOLOGICAS',
        first_leader_id=res_2.id,
        first_leader=res_2.name,
    )
    session.add_all([rg_1, rg_2])
    await session.commit()
    await session.refresh(rg_1)
    await session.refresh(rg_2)

    # 4. Consulta endpoint filtrando pela inst_1
    response_1 = await async_client.get(
        f'/research_group?institution_id={inst_1.id}'
    )
    assert response_1.status_code == HTTPStatus.OK
    data_1 = response_1.json()

    rg_1_ids = [item['id'] for item in data_1]
    assert str(rg_1.id) in rg_1_ids
    assert str(rg_2.id) not in rg_1_ids

    # 5. Consulta endpoint filtrando pela inst_2
    response_2 = await async_client.get(
        f'/research_group?institution_id={inst_2.id}'
    )
    assert response_2.status_code == HTTPStatus.OK
    data_2 = response_2.json()

    rg_2_ids = [item['id'] for item in data_2]
    assert str(rg_2.id) in rg_2_ids
    assert str(rg_1.id) not in rg_2_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_group_pagination_integration(session, async_client):
    acronym = f'P{uuid4().hex[:6].upper()}'
    inst = Institution(
        name=f'Universidade Pag {acronym}',
        acronym=acronym,
    )
    session.add(inst)
    await session.commit()
    await session.refresh(inst)

    res = Researcher(
        name=f'Lider Pag {acronym}',
        lattes_id=str(uuid4().int)[:16],
        institution_id=inst.id,
    )
    session.add(res)
    await session.commit()
    await session.refresh(res)

    rg_a = ResearchGroup(
        name=f'A Group {acronym}',
        institution=acronym,
        first_leader_id=res.id,
        first_leader=res.name,
    )
    rg_b = ResearchGroup(
        name=f'B Group {acronym}',
        institution=acronym,
        first_leader_id=res.id,
        first_leader=res.name,
    )
    session.add_all([rg_a, rg_b])
    await session.commit()
    await session.refresh(rg_a)
    await session.refresh(rg_b)

    # Page 1, length 1 -> Group A
    resp_p1 = await async_client.get(
        f'/research_group?institution_id={inst.id}&page=1&lenght=1'
    )
    assert resp_p1.status_code == HTTPStatus.OK
    data_p1 = resp_p1.json()
    assert len(data_p1) == 1
    assert data_p1[0]['id'] == str(rg_a.id)

    # Page 2, length 1 -> Group B
    resp_p2 = await async_client.get(
        f'/research_group?institution_id={inst.id}&page=2&lenght=1'
    )
    assert resp_p2.status_code == HTTPStatus.OK
    data_p2 = resp_p2.json()
    assert len(data_p2) == 1
    assert data_p2[0]['id'] == str(rg_b.id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_research_group_chart_endpoints_integration(
    session, async_client
):
    acronym = f'C{uuid4().hex[:6].upper()}'
    inst = Institution(
        name=f'Universidade Chart {acronym}',
        acronym=acronym,
    )
    session.add(inst)
    await session.commit()
    await session.refresh(inst)

    res = Researcher(
        name=f'Lider Chart {acronym}',
        lattes_id=str(uuid4().int)[:16],
        institution_id=inst.id,
    )
    session.add(res)
    await session.commit()
    await session.refresh(res)

    rg_1 = ResearchGroup(
        name=f'Chart Group 1 {acronym}',
        institution=acronym,
        area='CIENCIAS DA SAUDE',
        first_leader_id=res.id,
        first_leader=res.name,
    )
    rg_2 = ResearchGroup(
        name=f'Chart Group 2 {acronym}',
        institution=acronym,
        area='CIENCIAS DA SAUDE',
        first_leader_id=res.id,
        first_leader=res.name,
    )
    rg_3 = ResearchGroup(
        name=f'Chart Group 3 {acronym}',
        institution=acronym,
        area='ENGENHARIAS',
        first_leader_id=res.id,
        first_leader=res.name,
    )
    session.add_all([rg_1, rg_2, rg_3])
    await session.commit()

    # 1. Testa /research_group/chart
    resp_chart = await async_client.get(
        f'/research_group/chart?institution_id={inst.id}'
    )
    assert resp_chart.status_code == HTTPStatus.OK
    data_chart = resp_chart.json()
    expected_areas_count = 2
    expected_saude_count = 2
    assert len(data_chart) == expected_areas_count
    assert data_chart[0]['area'] == 'CIENCIAS DA SAUDE'
    assert data_chart[0]['count'] == expected_saude_count
    assert data_chart[1]['area'] == 'ENGENHARIAS'
    assert data_chart[1]['count'] == 1

    # 2. Testa /metrics/research-group/chart
    resp_metrics = await async_client.get(
        f'/metrics/research-group/chart?institution_id={inst.id}'
    )
    assert resp_metrics.status_code == HTTPStatus.OK
    data_metrics = resp_metrics.json()
    assert data_metrics == data_chart

    # 3. Testa /research_group/count com filtro
    resp_count = await async_client.get(
        f'/research_group/count?institution_id={inst.id}'
    )
    assert resp_count.status_code == HTTPStatus.OK
    assert resp_count.json() == data_chart
