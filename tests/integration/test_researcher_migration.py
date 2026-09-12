from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from simcc.core.db.models.institution import Institution
from simcc.core.db.models.researcher import Researcher
from simcc.core.db.models.researcher_institution import ResearcherInstitution


@pytest.mark.integration
@pytest.mark.asyncio
async def test_researcher_lattes_id_not_null_constraint(session):
    researcher_invalid = Researcher(
        name='Pesquisador Sem Lattes',
        lattes_id=None,  # type: ignore
    )
    session.add(researcher_invalid)

    # Inserção sem lattes_id deve falhar no commit
    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_researcher_institution_data_crud_and_cascade(session):
    # 1. Cria instituição e pesquisador válido com lattes_id único
    unique_acronym = f'U{uuid4().hex[:6].upper()}'
    inst = Institution(
        name=f'Universidade {unique_acronym}',
        acronym=unique_acronym,
    )
    session.add(inst)
    await session.commit()
    await session.refresh(inst)

    researcher = Researcher(
        name='Pesquisador Teste Instituicao',
        lattes_id='9999888877776666',
        institution_id=inst.id,
    )
    session.add(researcher)
    await session.commit()
    await session.refresh(researcher)

    # 2. Cria vínculo em researcher_institution
    inst_data = ResearcherInstitution(
        researcher_id=researcher.id,
        institution_id=inst.id,
        workload=Decimal('40.00'),
        identity_territory='PORTAL DO SERTAO',
    )
    session.add(inst_data)
    await session.commit()

    # 3. Testa deleção em cascata
    await session.delete(researcher)
    await session.commit()

    # Verifica remoção automática via CASCADE
    sql = (
        'SELECT count(*) FROM researcher_institution '
        'WHERE researcher_id = :rid'
    )
    result = await session.execute(text(sql), {'rid': str(researcher.id)})
    assert result.scalar() == 0
