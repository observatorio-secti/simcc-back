# ruff: noqa: PLR2004
"""Contrato v2 — Fase 0: erros, envelopes, ids, ordenação e catálogos."""

import uuid
from http import HTTPStatus

import pytest
from sqlalchemy import text

from simcc.v2.schemas.base import V2Model
from simcc.v2.services import mv_refresh_service


@pytest.mark.asyncio
async def test_not_found_uses_error_envelope(client):
    response = client.get(f'/v2/researcher/{uuid.uuid4()}')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        'error': {
            'code': 'not_found',
            'message': 'Pesquisador não encontrado.',
            'details': [],
        }
    }


@pytest.mark.asyncio
async def test_unknown_parameter_uses_error_envelope(client):
    response = client.get('/v2/researcher?nao_existe=1')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    error = response.json()['error']
    assert error['code'] == 'unknown_parameter'
    assert error['details'][0]['field'] == 'nao_existe'


@pytest.mark.asyncio
async def test_validation_error_lists_fields(client):
    response = client.get('/v2/researcher?per_page=1000')

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    error = response.json()['error']
    assert error['code'] == 'validation_error'
    assert error['details'][0]['field'] == 'per_page'


@pytest.mark.asyncio
async def test_researcher_has_id_and_absolute_image_url(
    client, researcher_factory
):
    researcher = await researcher_factory(name='Identificador Novo')

    item = client.get('/v2/researcher?q=Identificador').json()['data'][0]

    assert item['id'] == str(researcher.id)
    assert item['researcher_id'] == item['id']
    assert item['image_url'].startswith('http')
    assert item['image_url'].endswith(f'/v2/researcher/{researcher.id}/image')
    assert item['image'] == f'/v2/researcher/{researcher.id}/image'


@pytest.mark.asyncio
async def test_researcher_search_has_no_summary(client):
    body = client.get('/v2/researcher').json()

    assert 'summary' not in body


@pytest.mark.asyncio
async def test_detail_uses_data_meta_envelope(client, researcher_factory):
    researcher = await researcher_factory(name='Envelope Detalhe')

    body = client.get(f'/v2/researcher/{researcher.id}').json()

    assert set(body) == {'data', 'meta'}
    assert body['data']['id'] == str(researcher.id)
    assert {'took_ms', 'cached', 'timestamp', 'data_as_of'} <= set(
        body['meta']
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'query', ['sort_by=year&sort_order=asc', 'by=year&order=asc']
)
async def test_production_sort_accepts_new_and_legacy_names(client, query):
    response = client.get(f'/v2/production/book?{query}')

    assert response.status_code == HTTPStatus.OK, response.text
    assert response.json()['sort'] == {'by': 'year', 'order': 'asc'}
    assert response.json()['filters_applied'] is not None


@pytest.mark.asyncio
async def test_data_as_of_reads_refresh_metadata(session):
    await session.execute(
        text(
            'INSERT INTO mv_refresh_metadata (view_name, refreshed_at) '
            "VALUES ('mv_teste', '2026-11-01T10:00:00Z') "
            'ON CONFLICT (view_name) DO UPDATE '
            'SET refreshed_at = EXCLUDED.refreshed_at'
        )
    )
    await session.commit()
    mv_refresh_service.reset_data_as_of_cache()

    value = await mv_refresh_service.get_last_refresh_timestamp(session)

    assert value is not None
    assert value.year >= 2026
    mv_refresh_service.reset_data_as_of_cache()


def test_v2_model_turns_empty_strings_into_null():
    class Item(V2Model):
        name: str
        note: str | None = None

    item = Item(name='', note='None')

    assert not item.name
    assert item.note is None


@pytest.mark.asyncio
async def test_institution_list_envelope_and_detail(
    client, institution_factory, graduate_program_factory
):
    inst = await institution_factory(
        name='Universidade Detalhe', acronym='UDET'
    )
    await graduate_program_factory(institution_id=inst.id)

    body = client.get('/v2/institution?q=UDET').json()
    assert {'data', 'pagination', 'filters_applied', 'sort', 'meta'} <= set(
        body
    )
    assert body['sort'] == {'by': 'name', 'order': 'asc'}

    detail = client.get(f'/v2/institution/{inst.id}')
    assert detail.status_code == HTTPStatus.OK
    data = detail.json()['data']
    assert data['acronym'] == 'UDET'
    assert data['counts']['graduate_programs'] == 1

    missing = client.get(f'/v2/institution/{uuid.uuid4()}')
    assert missing.status_code == HTTPStatus.NOT_FOUND
    assert missing.json()['error']['code'] == 'not_found'


@pytest.mark.asyncio
async def test_graduate_program_hyphen_path_alias_facets_and_detail(
    client, graduate_program_factory, session
):
    gp = await graduate_program_factory(
        name='Programa Hifen', acronym='PHIF', modality='Profissional'
    )
    await session.execute(
        text(
            'INSERT INTO research_lines_programs '
            '(graduate_program_id, name, area) '
            "VALUES (:id, 'Linha A', 'Computação')"
        ),
        {'id': gp.graduate_program_id},
    )
    await session.commit()

    new = client.get('/v2/graduate-program?q=PHIF&facets=modality').json()
    old = client.get('/v2/graduate_program?q=PHIF').json()
    assert new['data'] == old['data']
    assert new['data'][0]['modality'] == 'Profissional'
    assert new['facets']['modality']['param'] == 'modality'

    detail = client.get(
        f'/v2/graduate-program/{gp.graduate_program_id}'
    ).json()['data']
    assert detail['research_lines'][0]['name'] == 'Linha A'
    assert detail['institution'] is not None


@pytest.mark.asyncio
async def test_v2_openapi_declares_error_and_deprecations(client):
    schema = client.get('/v2/openapi.json').json()

    researcher = schema['components']['schemas']['ResearcherSummary']
    assert researcher['properties']['researcher_id']['deprecated'] is True
    assert researcher['properties']['image']['deprecated'] is True
    detail = schema['paths']['/researcher/{researcher_id}']['get']
    assert '404' in detail['responses']
    assert '/graduate-program' in schema['paths']
    assert '/graduate_program' not in schema['paths']
