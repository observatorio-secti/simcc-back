# ruff: noqa: PLR2004
"""Testes de `group_by` e filtros em `/v2/metrics/production/{kind}`."""

import uuid
from http import HTTPStatus

import pytest
from sqlalchemy import text


async def _refresh(session, view: str) -> None:
    await session.commit()
    await session.execute(text(f'REFRESH MATERIALIZED VIEW {view};'))
    await session.commit()


@pytest.mark.asyncio
async def test_article_metric_group_by_qualis_and_filter(
    client, session, researcher_factory
):
    researcher = await researcher_factory(name='Pesquisador Artigos')
    mag_id = uuid.uuid4()
    await session.execute(
        text(
            'INSERT INTO periodical_magazine (id, name, issn, qualis) '
            "VALUES (:id, 'Revista Teste', '1234-5678', 'A1')"
        ),
        {'id': mag_id},
    )
    articles = [
        ('Artigo A1 2020', 2020, 'A1'),
        ('Artigo A1 bis 2020', 2020, 'A1'),
        ('Artigo SQ 2020', 2020, 'SQ'),
        ('Artigo NP 2021', 2021, 'NP'),
        ('Artigo Sem Qualis 2021', 2021, None),
    ]
    for idx, (title, year, qualis) in enumerate(articles):
        prod_id = uuid.uuid4()
        await session.execute(
            text(
                'INSERT INTO bibliographic_production '
                '(id, sequence_code, title, type, year, year_, '
                'researcher_id, doi) '
                "VALUES (:id, :seq, :title, 'ARTICLE', :y, :y_int, :r, :doi)"
            ),
            {
                'id': prod_id,
                'seq': idx,
                'title': title,
                'y': str(year),
                'y_int': year,
                'r': researcher.id,
                'doi': f'10.1000/{idx}',
            },
        )
        await session.execute(
            text(
                'INSERT INTO bibliographic_production_article '
                '(bibliographic_production_id, periodical_magazine_id, '
                'qualis) VALUES (:id, :mag_id, :qualis)'
            ),
            {'id': prod_id, 'mag_id': mag_id, 'qualis': qualis},
        )
    await _refresh(session, 'mv_canonical_articles')

    # Sem group_by: contrato retrocompatível (sem group_by nem groups)
    plain = client.get(
        f'/v2/metrics/production/article?researcher_id={researcher.id}'
    )
    assert plain.status_code == HTTPStatus.OK
    plain_json = plain.json()
    assert 'group_by' not in plain_json
    assert plain_json['data'] == [
        {'period': 2020, 'value': 3},
        {'period': 2021, 'value': 2},
    ]

    # Com group_by=qualis
    grouped = client.get(
        f'/v2/metrics/production/article?researcher_id={researcher.id}'
        '&group_by=qualis'
    )
    assert grouped.status_code == HTTPStatus.OK
    grouped_json = grouped.json()
    assert grouped_json['kind'] == 'article'
    assert grouped_json['group_by'] == 'qualis'
    assert grouped_json['data'] == [
        {
            'period': 2020,
            'value': 3,
            'groups': {'A1': 2, 'not_rated': 1},
        },
        {
            'period': 2021,
            'value': 2,
            'groups': {'not_applicable': 1},
        },
    ]

    # Filtro alinhado: qualis=A1&qualis=not_rated deve bater com a listagem
    filtered_metric = client.get(
        f'/v2/metrics/production/article?researcher_id={researcher.id}'
        '&group_by=qualis&qualis=A1&qualis=not_rated'
    )
    assert filtered_metric.status_code == HTTPStatus.OK
    fm_json = filtered_metric.json()
    assert fm_json['filters_applied']['qualis'] == ['A1', 'not_rated']
    assert fm_json['data'] == [
        {
            'period': 2020,
            'value': 3,
            'groups': {'A1': 2, 'not_rated': 1},
        }
    ]

    listed = client.get(
        f'/v2/production/article?researcher_id={researcher.id}'
        '&qualis=A1&qualis=not_rated'
    ).json()
    assert sum(pt['value'] for pt in fm_json['data']) == (
        listed['pagination']['total_items']
    )


@pytest.mark.asyncio
async def test_guidance_metric_group_by_nature_and_status(
    client, session, researcher_factory
):
    researcher = await researcher_factory(name='Orientador Métrica')
    rows = [
        ('Orientação 1', 'Dissertação de mestrado', 'Concluída', 2022),
        ('Orientação 2', 'Tese de doutorado', 'Concluída', 2022),
        ('Orientação 3', 'Tese de doutorado', 'Em andamento', 2023),
    ]
    for seq, (title, nature, status, year) in enumerate(rows):
        await session.execute(
            text(
                'INSERT INTO guidance (researcher_id, sequence_code, title, '
                'nature, type, status, oriented, year) '
                "VALUES (:r, :s, :t, :n, 'Orientador principal', :st, "
                "'Aluno', :y)"
            ),
            {
                'r': researcher.id,
                's': seq,
                't': title,
                'n': nature,
                'st': status,
                'y': year,
            },
        )
    await _refresh(session, 'mv_canonical_guidance')

    by_nature = client.get(
        f'/v2/metrics/production/guidance?researcher_id={researcher.id}'
        '&group_by=nature'
    )
    assert by_nature.status_code == HTTPStatus.OK
    assert by_nature.json()['group_by'] == 'nature'
    assert by_nature.json()['data'] == [
        {
            'period': 2022,
            'value': 2,
            'groups': {
                'Dissertação de mestrado': 1,
                'Tese de doutorado': 1,
            },
        },
        {
            'period': 2023,
            'value': 1,
            'groups': {'Tese de doutorado': 1},
        },
    ]

    by_status = client.get(
        f'/v2/metrics/production/guidance?researcher_id={researcher.id}'
        '&group_by=status&status=Concluída'
    )
    assert by_status.status_code == HTTPStatus.OK
    assert by_status.json()['filters_applied']['status'] == ['Concluída']
    assert by_status.json()['data'] == [
        {
            'period': 2022,
            'value': 2,
            'groups': {'Concluída': 2},
        }
    ]


@pytest.mark.asyncio
async def test_event_metric_group_by_nature_and_type_participation(
    client, session, researcher_factory
):
    researcher = await researcher_factory(name='Participante Eventos')
    rows = [
        ('Evento 1', 'Congresso', 'Apresentação Oral', 2021),
        ('Evento 2', 'Seminário', 'Ouvinte', 2021),
        ('Evento 3', 'Congresso', 'Pôster', 2022),
    ]
    for seq, (title, nature, tp, year) in enumerate(rows):
        await session.execute(
            text(
                'INSERT INTO participation_events '
                '(id, sequence_code, title, event_name, nature, '
                'type_participation, form_participation, year, researcher_id) '
                'VALUES (:id, :seq, :t, :t, :n, :tp, :fp, :y, :r)'
            ),
            {
                'id': uuid.uuid4(),
                'seq': seq,
                't': title,
                'n': nature,
                'tp': tp,
                'fp': 'Participante',
                'y': str(year),
                'r': researcher.id,
            },
        )
    await _refresh(session, 'mv_canonical_events')

    by_nature = client.get(
        f'/v2/metrics/production/event?researcher_id={researcher.id}'
        '&group_by=nature'
    )
    assert by_nature.status_code == HTTPStatus.OK
    assert by_nature.json()['data'] == [
        {
            'period': 2021,
            'value': 2,
            'groups': {'Congresso': 1, 'Seminário': 1},
        },
        {
            'period': 2022,
            'value': 1,
            'groups': {'Congresso': 1},
        },
    ]

    by_tp = client.get(
        f'/v2/metrics/production/event?researcher_id={researcher.id}'
        '&group_by=type_participation&nature=Congresso'
    )
    assert by_tp.status_code == HTTPStatus.OK
    assert by_tp.json()['data'] == [
        {
            'period': 2021,
            'value': 1,
            'groups': {'Apresentação Oral': 1},
        },
        {
            'period': 2022,
            'value': 1,
            'groups': {'Pôster': 1},
        },
    ]


@pytest.mark.asyncio
async def test_research_project_metric_group_by_status_and_nature(
    client, session, researcher_factory
):
    researcher = await researcher_factory(name='Coordenador Projeto')
    rows = [
        ('Projeto A', 2019, 'CONCLUIDO', 'PESQUISA'),
        ('Projeto B', 2019, 'EM_ANDAMENTO', 'EXTENSAO'),
        ('Projeto C', 2021, 'EM_ANDAMENTO', 'PESQUISA'),
    ]
    for seq, (title, start_year, status, nature) in enumerate(rows):
        await session.execute(
            text(
                'INSERT INTO research_project '
                '(id, sequence_code, researcher_id, project_name, start_year, '
                'status, nature) '
                'VALUES (:id, :seq, :r, :t, :sy, :st, :n)'
            ),
            {
                'id': uuid.uuid4(),
                'seq': seq,
                'r': researcher.id,
                't': title,
                'sy': start_year,
                'st': status,
                'n': nature,
            },
        )
    await _refresh(session, 'mv_canonical_research_projects')

    by_status = client.get(
        f'/v2/metrics/production/research-project?researcher_id={researcher.id}'
        '&group_by=status'
    )
    assert by_status.status_code == HTTPStatus.OK
    assert by_status.json()['kind'] == 'research_project'
    assert by_status.json()['group_by'] == 'status'
    assert by_status.json()['data'] == [
        {
            'period': 2019,
            'value': 2,
            'groups': {'CONCLUIDO': 1, 'EM_ANDAMENTO': 1},
        },
        {
            'period': 2021,
            'value': 1,
            'groups': {'EM_ANDAMENTO': 1},
        },
    ]

    by_nature = client.get(
        f'/v2/metrics/production/research-project?researcher_id={researcher.id}'
        '&group_by=nature&status=EM_ANDAMENTO'
    )
    assert by_nature.status_code == HTTPStatus.OK
    assert by_nature.json()['data'] == [
        {'period': 2019, 'value': 1, 'groups': {'EXTENSAO': 1}},
        {'period': 2021, 'value': 1, 'groups': {'PESQUISA': 1}},
    ]


@pytest.mark.asyncio
async def test_metric_invalid_group_by_and_invalid_filter_return_422(client):
    unsupported_kind = client.get(
        '/v2/metrics/production/book?group_by=qualis'
    )
    assert unsupported_kind.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    err = unsupported_kind.json()['error']
    assert err['code'] == 'invalid_group_by'

    unsupported_dim = client.get(
        '/v2/metrics/production/article?group_by=status'
    )
    assert unsupported_dim.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert unsupported_dim.json()['error']['code'] == 'invalid_group_by'

    unsupported_filter = client.get(
        '/v2/metrics/production/book?qualis=A1'
    )
    assert unsupported_filter.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert unsupported_filter.json()['error']['code'] == 'unknown_parameter'
