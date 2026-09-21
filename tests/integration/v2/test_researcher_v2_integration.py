# ruff: noqa: PLR2004
from http import HTTPStatus
from uuid import uuid4

import pytest

from simcc.core.db.models.institution import Institution
from simcc.core.db.models.researcher import Researcher


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_researcher_v2_integration(session, async_client):
    # 1. Cria instituição de teste
    unique_acronym = f'V2{uuid4().hex[:4].upper()}'
    inst = Institution(
        name=f'Universidade V2 {unique_acronym}',
        acronym=unique_acronym,
    )
    session.add(inst)
    await session.commit()
    await session.refresh(inst)

    # 2. Cria pesquisadores de teste
    r1 = Researcher(
        name='Alice V2 Pesquisadora',
        lattes_id=str(uuid4().int)[:16],
        institution_id=inst.id,
    )
    r2 = Researcher(
        name='Bernardo V2 Pesquisador',
        lattes_id=str(uuid4().int)[:16],
        institution_id=inst.id,
    )
    session.add_all([r1, r2])
    await session.commit()
    await session.refresh(r1)
    await session.refresh(r2)

    # 3. Requisição para /v2/researcher filtrando por instituição
    response = await async_client.get(
        f'/v2/researcher?institution_id={inst.id}&sort_by=name&sort_order=asc'
    )
    assert response.status_code == HTTPStatus.OK

    body = response.json()
    assert 'data' in body
    assert 'pagination' in body
    assert 'filters_applied' in body
    assert 'sort' in body
    assert 'meta' in body

    # Valida paginação
    assert body['pagination']['page'] == 1
    assert body['pagination']['per_page'] == 20
    assert body['pagination']['total_items'] >= 2
    assert body['filters_applied']['institution_id'] == str(inst.id)
    assert body['sort']['by'] == 'name'
    assert body['sort']['order'] == 'asc'
    assert body['meta']['took_ms'] >= 1
    assert body['meta']['cached'] is False

    # Valida formato dos dados (apenas researcher_id e name)
    names = [item['name'] for item in body['data']]
    assert 'Alice V2 Pesquisadora' in names
    assert 'Bernardo V2 Pesquisador' in names
    for item in body['data']:
        assert 'researcher_id' in item
        assert 'name' in item

    # 4. Testa busca por termo q
    resp_search = await async_client.get(
        f'/v2/researcher?q=Alice&institution_id={inst.id}'
    )
    assert resp_search.status_code == HTTPStatus.OK
    body_search = resp_search.json()
    assert len(body_search['data']) == 1
    assert body_search['data'][0]['name'] == 'Alice V2 Pesquisadora'
    assert body_search['data'][0]['researcher_id'] == str(r1.id)

    # 5. Testa paginação (per_page=1)
    resp_page = await async_client.get(
        f'/v2/researcher?institution_id={inst.id}&page=1&per_page=1&sort_by=name&sort_order=asc'
    )
    assert resp_page.status_code == HTTPStatus.OK
    body_page = resp_page.json()
    assert len(body_page['data']) == 1
    assert body_page['pagination']['page'] == 1
    assert body_page['pagination']['per_page'] == 1
    assert body_page['pagination']['total_pages'] >= 2
    assert body_page['pagination']['has_next'] is True
    assert body_page['pagination']['has_prev'] is False
    assert body_page['data'][0]['name'] == 'Alice V2 Pesquisadora'
