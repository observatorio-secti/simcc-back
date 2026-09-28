# ruff: noqa: PLR2004
import uuid
from http import HTTPStatus

import pytest
from sqlalchemy import event

from simcc.core import utils
from simcc.core.db.models.graduate_program import GraduateProgramResearcher
from simcc.core.db.models.openalex import OpenAlexResearcher
from simcc.core.db.models.research_group import (
    ResearchGroup,
    ResearchGroupResearcher,
)
from simcc.core.db.models.researcher import ResearcherProduction


async def _add_production(session, refresh_mvs, researcher_id, **counts):
    session.add(ResearcherProduction(researcher_id=researcher_id, **counts))
    await session.commit()
    await refresh_mvs()


@pytest.mark.asyncio
async def test_list_returns_summary_card(
    client, session, researcher_factory, refresh_mvs
):
    researcher = await researcher_factory(
        name='Card Completo', graduation='Doutorado', classification='E+'
    )
    await _add_production(
        session,
        refresh_mvs,
        researcher.id,
        articles=5,
        book_chapters=2,
        book=1,
    )

    item = client.get('/v2/researcher?q=Card').json()['data'][0]

    assert item['image'] == f'/v2/researcher/{researcher.id}/image'
    assert item['graduation'] == 'Doutorado'
    assert item['classification'] == 'E+'
    assert item['lattes_update'] is not None
    assert item['counts'] == {
        'articles': 5,
        'book_chapters': 2,
        'books': 1,
        'patents': 0,
        'software': 0,
        'brands': 0,
    }
    for heavy_field in ('abstract', 'identifiers', 'graduate_programs'):
        assert heavy_field not in item


@pytest.mark.asyncio
async def test_list_counts_default_to_zero_without_production(
    client, researcher_factory
):
    await researcher_factory(name='Sem Producao')

    item = client.get('/v2/researcher').json()['data'][0]

    assert set(item['counts'].values()) == {0}


@pytest.mark.asyncio
async def test_detail_not_found(client):
    response = client.get(f'/v2/researcher/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_detail_minimal_profile(client, researcher_factory):
    researcher = await researcher_factory(
        name='Perfil Minimo', lattes_10_id='K1234567A8'
    )

    body = client.get(f'/v2/researcher/{researcher.id}').json()

    assert body['researcher_id'] == str(researcher.id)
    assert body['identifiers'] == {
        'lattes_id': researcher.lattes_id,
        'lattes_10_id': 'K1234567A8',
        'orcid': None,
        'scopus': None,
        'openalex': None,
    }
    assert body['bibliometrics'] is None
    assert body['affiliations'] == []
    assert body['graduate_programs'] == []
    assert body['research_groups'] == []
    assert set(body['counts'].values()) == {0}
    assert 'matches' not in body


@pytest.mark.asyncio
async def test_detail_full_profile(  # noqa: PLR0913, PLR0917
    client,
    session,
    researcher_factory,
    institution_factory,
    graduate_program_factory,
):
    institution = await institution_factory(name='Instituto Perfil')
    researcher = await researcher_factory(
        name='Perfil Completo',
        abstract='Resumo do Lattes',
        abstract_ai='Resumo por IA',
        institution_id=institution.id,
    )
    gp = await graduate_program_factory(name='Programa Perfil', acronym='PP')
    group = ResearchGroup(name='Grupo Perfil')
    session.add(group)
    await session.flush()
    session.add_all([
        ResearcherProduction(researcher_id=researcher.id, articles=3),
        OpenAlexResearcher(
            researcher_id=researcher.id,
            h_index=7,
            i10_index=4,
            cited_by_count=120,
            works_count=30,
            scopus='SCOPUS-1',
            openalex='A123',
        ),
        GraduateProgramResearcher(
            graduate_program_id=gp.graduate_program_id,
            researcher_id=researcher.id,
            type_='PERMANENTE',
        ),
        ResearchGroupResearcher(
            research_group_id=group.id, researcher_id=researcher.id
        ),
    ])
    await session.commit()

    body = client.get(f'/v2/researcher/{researcher.id}').json()

    assert body['abstract'] == 'Resumo do Lattes'
    assert body['abstract_ai'] == 'Resumo por IA'
    assert body['counts']['articles'] == 3
    assert body['identifiers']['scopus'] == 'SCOPUS-1'
    assert body['identifiers']['openalex'] == 'A123'
    assert body['bibliometrics'] == {
        'h_index': 7,
        'i10_index': 4,
        'cited_by_count': 120,
        'works_count': 30,
    }
    assert body['affiliations'][0]['institution']['name'] == (
        'Instituto Perfil'
    )
    assert body['graduate_programs'] == [
        {
            'program': {
                'id': str(gp.graduate_program_id),
                'name': 'Programa Perfil',
                'acronym': 'PP',
            },
            'type': 'PERMANENTE',
        }
    ]
    assert body['research_groups'] == [
        {'id': str(group.id), 'name': 'Grupo Perfil'}
    ]


@pytest.mark.asyncio
async def test_detail_query_budget(client, researcher_factory, engine):
    researcher = await researcher_factory()
    statements = []

    def count_queries(*args, **kwargs):
        statement = args[2] if len(args) > 2 else kwargs.get('statement', '')
        if statement.strip().upper().startswith('SELECT'):
            statements.append(statement)

    event.listen(engine.sync_engine, 'before_cursor_execute', count_queries)
    try:
        response = client.get(f'/v2/researcher/{researcher.id}')
    finally:
        event.remove(
            engine.sync_engine, 'before_cursor_execute', count_queries
        )

    assert response.status_code == HTTPStatus.OK
    # perfil + vínculos + programas + grupos
    assert len(statements) == 4


@pytest.mark.asyncio
async def test_image_serves_cached_file(
    client, researcher_factory, tmp_path, monkeypatch
):
    monkeypatch.setattr(utils, 'RESEARCHER_IMAGE_DIR', tmp_path)
    researcher = await researcher_factory()
    (tmp_path / f'{researcher.id}.jpg').write_bytes(b'fake-jpeg')

    response = client.get(f'/v2/researcher/{researcher.id}/image')

    assert response.status_code == HTTPStatus.OK
    assert response.content == b'fake-jpeg'


@pytest.mark.asyncio
async def test_image_not_found_without_lattes_10_id(
    client, researcher_factory, tmp_path, monkeypatch
):
    monkeypatch.setattr(utils, 'RESEARCHER_IMAGE_DIR', tmp_path)
    researcher = await researcher_factory()

    response = client.get(f'/v2/researcher/{researcher.id}/image')

    assert response.status_code == HTTPStatus.NOT_FOUND
