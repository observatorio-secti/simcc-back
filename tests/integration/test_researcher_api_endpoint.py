from decimal import Decimal
from http import HTTPStatus
from uuid import uuid4

import pytest

from simcc.core.db.models.institution import Institution
from simcc.core.db.models.researcher import Researcher
from simcc.core.db.models.researcher_institution import ResearcherInstitution


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_researchers_by_institution_endpoint(session, async_client):
    # 1. Cria instituição com acrônimo único
    unique_acronym = f'U{uuid4().hex[:6].upper()}'
    inst = Institution(
        name=f'Universidade {unique_acronym}',
        acronym=unique_acronym,
    )
    session.add(inst)
    await session.commit()
    await session.refresh(inst)

    # 2. Cria pesquisador e vínculo institucional
    unique_lattes = str(uuid4().int)[:16]
    researcher = Researcher(
        name='Pesquisador Endpoint Integracao',
        lattes_id=unique_lattes,
        institution_id=inst.id,
    )
    session.add(researcher)
    await session.commit()
    await session.refresh(researcher)

    inst_data = ResearcherInstitution(
        researcher_id=researcher.id,
        institution_id=inst.id,
        workload=Decimal('40.00'),
        identity_territory='METROPOLITANA DE SALVADOR',
    )
    session.add(inst_data)
    await session.commit()

    # 3. Chama endpoint /researcher com institution_id
    response = await async_client.get(f'/researcher?institution_id={inst.id}')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) >= 1

    # Valida exposição de dados institucionais dentro de institution
    expected_workload = 40.0
    matched = next((r for r in data if r['id'] == str(researcher.id)), None)
    assert matched is not None
    assert matched['name'] == 'Pesquisador Endpoint Integracao'
    assert matched['institution'] is not None
    assert matched['institution']['workload'] == expected_workload
    assert (
        matched['institution']['identity_territory']
        == 'METROPOLITANA DE SALVADOR'
    )
