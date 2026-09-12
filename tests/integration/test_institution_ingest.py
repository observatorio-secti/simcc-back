from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from scripts.ingest.ingest_researcher_affiliations import import_rows
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.location import City, Country, State
from simcc.core.db.models.researcher import Researcher


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingest_affiliations_with_real_session(session):  # noqa: PLR0914
    # 1. Cria País, Estado e Cidade para resolução
    country = Country(
        name='Brasil',
        name_pt='Brasil',
        alpha_2_code='BR',
        alpha_3_code='BRA',
    )
    session.add(country)
    await session.commit()
    await session.refresh(country)

    state = State(
        name='Bahia',
        abbreviation='BA',
        country_id=country.id,
    )
    session.add(state)
    await session.commit()
    await session.refresh(state)

    city = City(
        name='Salvador',
        state_id=state.id,
        country_id=country.id,
    )
    session.add(city)
    await session.commit()
    await session.refresh(city)

    # Cria instituição de teste
    unique_acronym = f'U{uuid4().hex[:6].upper()}'
    inst = Institution(
        name=f'Universidade {unique_acronym}',
        acronym=unique_acronym,
    )
    session.add(inst)
    await session.commit()
    await session.refresh(inst)

    # 2. Cria pesquisador no banco com lattes_id único
    unique_lattes = str(uuid4().int)[:16]
    researcher = Researcher(
        name='Pesquisador Teste Ingestao',
        lattes_id=unique_lattes,
        institution_id=inst.id,
    )
    session.add(researcher)
    await session.commit()
    await session.refresh(researcher)

    # 3. Prepara linhas de teste
    rows = [
        {
            '_line': 2,
            'name': 'Pesquisador Teste Ingestao',
            'lattes_id': unique_lattes,
            'workload': '40',
            'city': 'Salvador',
            'zip_code': None,
            'identity_territory': 'METROPOLITANA DE SALVADOR',
        },
        {
            '_line': 3,
            'name': 'Desconhecido',
            'lattes_id': '0000000000000000',
            'workload': '20',
            'city': 'Salvador',
            'zip_code': None,
            'identity_territory': 'METROPOLITANA DE SALVADOR',
        },
    ]

    territories = {'salvador': 'METROPOLITANA DE SALVADOR'}

    # 4. Executa ingestão
    report = await import_rows(
        session=session,
        rows=rows,
        institution_id=inst.id,
        resolver=None,
        territories=territories,
        dry_run=False,
        acronym=inst.acronym,
    )

    statuses = [r['status'] for r in report]
    assert statuses.count('atualizado') == 1
    assert statuses.count('ignorado') == 1

    # 5. Verifica dados em researcher_institution
    sql_select = (
        'SELECT workload, identity_territory, city_id '
        'FROM researcher_institution '
        'WHERE researcher_id = :rid AND institution_id = :iid'
    )
    res = await session.execute(
        text(sql_select),
        {'rid': str(researcher.id), 'iid': str(inst.id)},
    )
    row = res.mappings().one()
    assert row['workload'] == Decimal('40.00')
    assert row['identity_territory'] == 'METROPOLITANA DE SALVADOR'
    assert row['city_id'] == city.id

    # 6. Garante que researcher.city_id NÃO foi alterado
    await session.refresh(researcher)
    assert researcher.city_id is None

    # 7. Testa idempotência (reexecução)
    report2 = await import_rows(
        session=session,
        rows=rows,
        institution_id=inst.id,
        resolver=None,
        territories=territories,
        dry_run=False,
        acronym=inst.acronym,
    )
    statuses2 = [r['status'] for r in report2]
    assert statuses2.count('atualizado') == 1
    assert statuses2.count('ignorado') == 1

    # Continua havendo exatamente 1 registro
    sql_count = (
        'SELECT count(*) FROM researcher_institution '
        'WHERE researcher_id = :rid AND institution_id = :iid'
    )
    count_res = await session.execute(
        text(sql_count),
        {'rid': str(researcher.id), 'iid': str(inst.id)},
    )
    assert count_res.scalar() == 1
