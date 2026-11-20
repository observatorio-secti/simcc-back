# ruff: noqa: PLR2004
"""Tipos de produção novos da v2: marcas, orientações e relatórios."""

import uuid
from http import HTTPStatus

import pytest
from sqlalchemy import text


async def _refresh(session, view: str):
    await session.commit()
    await session.execute(text(f'REFRESH MATERIALIZED VIEW {view};'))
    await session.commit()


@pytest.mark.asyncio
async def test_brand_dedup_filter_facet_and_detail(
    client, session, researcher_factory
):
    r1 = await researcher_factory(name='Titular Um')
    r2 = await researcher_factory(name='Titular Dois')
    for seq, rid in enumerate((r1.id, r2.id)):
        await session.execute(
            text(
                'INSERT INTO brand (researcher_id, sequence_code, title, '
                'nature, goal, year) VALUES (:r, :s, :t, :n, :g, 2021)'
            ),
            {
                'r': rid,
                's': seq,
                't': 'Marca Ciclone',
                'n': 'Produto',
                'g': 'Proteger o nome do software',
            },
        )
    await _refresh(session, 'mv_canonical_brands')

    body = client.get(
        '/v2/production/brand?q=ciclone&facets=nature,year'
    ).json()

    assert body['pagination']['total_items'] == 1
    brand = body['data'][0]
    assert brand['nature'] == 'Produto'
    assert {a['id'] for a in brand['platform_authors']} == {
        str(r1.id),
        str(r2.id),
    }
    assert body['facets']['nature']['param'] == 'nature'
    assert body['facets']['nature']['items'][0]['count'] == 1

    by_researcher = client.get(
        f'/v2/production/brand?researcher_id={r1.id}'
    ).json()
    assert by_researcher['pagination']['total_items'] == 1

    other_nature = client.get('/v2/production/brand?nature=Servico').json()
    assert other_nature['data'] == []

    detail = client.get(f'/v2/production/brand/{brand["id"]}')
    assert detail.status_code == HTTPStatus.OK
    assert detail.json()['data']['goal'] == 'Proteger o nome do software'


@pytest.mark.asyncio
async def test_guidance_filters_by_status(
    client, session, researcher_factory
):
    researcher = await researcher_factory(name='Orientador Teste')
    for seq, (title, status) in enumerate(
        (
            ('Redes neurais para solos', 'Concluída'),
            ('Clima e agricultura', 'Em andamento'),
        )
    ):
        await session.execute(
            text(
                'INSERT INTO guidance (researcher_id, sequence_code, title, '
                'nature, type, status, oriented, year) '
                "VALUES (:r, :s, :t, 'Dissertação de mestrado', "
                "'Orientador principal', :st, 'Aluno X', 2023)"
            ),
            {'r': researcher.id, 's': seq, 't': title, 'st': status},
        )
    await _refresh(session, 'mv_canonical_guidance')

    done = client.get(
        f'/v2/production/guidance?researcher_id={researcher.id}'
        '&status=Concluída'
    ).json()

    assert [g['title'] for g in done['data']] == ['Redes neurais para solos']
    assert done['data'][0]['oriented'] == 'Aluno X'
    assert done['filters_applied']['status'] == ['Concluída']


@pytest.mark.asyncio
async def test_report_search_and_missing_detail(
    client, session, researcher_factory
):
    researcher = await researcher_factory(name='Autor Relatorio')
    await session.execute(
        text(
            'INSERT INTO research_report (researcher_id, sequence_code, '
            'title, project_name, financing_institutionc, year) '
            "VALUES (:r, 1, 'Relatório de qualidade da água', "
            "'Projeto Rio Limpo', 'FAPESB', 2020)"
        ),
        {'r': researcher.id},
    )
    await _refresh(session, 'mv_canonical_reports')

    body = client.get('/v2/production/report?q=água').json()
    assert body['data'][0]['project_name'] == 'Projeto Rio Limpo'

    detail = client.get(
        f'/v2/production/report/{body["data"][0]["id"]}'
    ).json()
    assert detail['data']['financing'] == 'FAPESB'

    missing = client.get(f'/v2/production/report/{uuid.uuid4()}')
    assert missing.status_code == HTTPStatus.NOT_FOUND
    assert missing.json()['error']['code'] == 'not_found'
