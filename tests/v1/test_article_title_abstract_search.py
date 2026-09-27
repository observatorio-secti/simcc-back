from functools import partial
from http import HTTPStatus
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from simcc.v1.queries import external_query, metrics_query
from simcc.v1.queries.institution_query import InstitutionFrequencyQuery
from simcc.v1.repositories import tools

ARTICLE_DENGUE = SimpleNamespace(type='ARTICLE', term='dengue')


def _researcher_names(response):
    assert response.status_code == HTTPStatus.OK
    return {r['name'] for r in response.json()}


def _article_titles(response):
    assert response.status_code == HTTPStatus.OK
    return {a['title'] for a in response.json()}


@pytest.mark.asyncio
async def test_researcher_search_matches_openalex_abstract(
    client, researcher_factory, article_factory
):
    by_title = await researcher_factory(name='Por Titulo')
    by_abstract = await researcher_factory(name='Por Resumo')
    unrelated = await researcher_factory(name='Sem Relacao')
    await article_factory(
        by_title,
        'Vigilancia da dengue urbana',
    )
    await article_factory(
        by_abstract,
        'Estudo epidemiologico regional',
        abstract='Analisamos surtos de dengue em cidades do nordeste.',
    )
    await article_factory(
        unrelated, 'Redes neurais', abstract='Aprendizado profundo.'
    )

    response = client.get('/researchers?type=ARTICLE&term=dengue')

    assert _researcher_names(response) == {'Por Titulo', 'Por Resumo'}


@pytest.mark.asyncio
async def test_article_list_matches_title_and_abstract(
    client, researcher_factory, article_factory
):
    researcher = await researcher_factory(lattes_10_id='K0000000A1')
    await article_factory(researcher, 'Dengue no semiarido')
    await article_factory(
        researcher,
        'Arboviroses emergentes',
        abstract='Casos de dengue notificados entre 2015 e 2020.',
    )
    await article_factory(
        researcher, 'Clima e agricultura', abstract='Seca prolongada.'
    )

    response = client.get('/production/article?term=dengue')

    assert _article_titles(response) == {
        'Dengue no semiarido',
        'Arboviroses emergentes',
    }


@pytest.mark.asyncio
async def test_terms_combine_across_title_and_abstract(
    client, researcher_factory, article_factory
):
    researcher = await researcher_factory(lattes_10_id='K0000000A1')
    await article_factory(
        researcher, 'Dengue em criancas', abstract='Coinfeccao por zika.'
    )
    await article_factory(researcher, 'Dengue em adultos')

    # `;` é AND na sintaxe da v1
    response = client.get('/production/article?term=dengue;zika')

    assert _article_titles(response) == {'Dengue em criancas'}


@pytest.mark.asyncio
async def test_book_search_ignores_openalex_abstract(
    client, researcher_factory, article_factory
):
    researcher = await researcher_factory(name='Autor Livro')
    book = await article_factory(
        researcher, 'Historia do sertao', type_='BOOK'
    )
    # Mesmo que exista um resumo associado, livros continuam só por título
    await article_factory(
        researcher, 'Outro titulo', abstract='sertao', type_='BOOK'
    )

    response = client.get('/researchers/books?term=sertao')

    assert _researcher_names(response) == {'Autor Livro'}
    assert book.title == 'Historia do sertao'


SAMPLE_ROWS = """
    (VALUES
        ('titulo', 'dengue urbana', NULL),
        ('resumo', 'outro assunto', 'surto de dengue'),
        ('nenhum', 'outro assunto', 'sem relacao')
    ) AS t(name, title, abstract)
"""


@pytest.mark.asyncio
async def test_title_weighs_more_than_abstract(session):
    filter_sql, params = tools.title_abstract_filter(
        't.title', 't.abstract', 'dengue'
    )
    # O filtro usa placeholders no estilo %(nome)s; o text() usa :nome
    filter_sql = filter_sql.replace('%(', ':').replace(')s', '')
    rank_sql = filter_sql.removeprefix(' AND (').rsplit('> 0.04', 1)[0]

    rows = (
        await session.execute(
            text(
                f"""
                SELECT t.name, {rank_sql} AS rank
                FROM {SAMPLE_ROWS}
                WHERE 1 = 1 {filter_sql}
                """
            ),
            params,
        )
    ).all()
    ranks = dict(rows)

    assert set(ranks) == {'titulo', 'resumo'}
    assert ranks['titulo'] == pytest.approx(ranks['resumo'] / 0.7)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'build_query',
    [
        metrics_query.ResearcherMetricsQuery,
        partial(
            metrics_query.YearlyProductionMetricsQuery,
            production_type='ARTICLE',
        ),
    ],
    ids=['researcher_metrics', 'article_metrics'],
)
async def test_other_article_queries_execute_with_abstract(
    session, researcher_factory, article_factory, build_query
):
    researcher = await researcher_factory()
    await article_factory(
        researcher, 'Estudo regional', abstract='Surto de dengue.'
    )

    query = build_query(session)
    query.apply_filters(ARTICLE_DENGUE)
    await query.execute()

    assert tools.TITLE_ABSTRACT_RANK_WEIGHTS in query.build_sql()


def test_ufmg_docentes_query_uses_abstract():
    # O schema `ufmg` não existe no banco de testes; valida o SQL gerado
    query = external_query.DocenteSearchQuery(session=None)
    query.apply_filters(ARTICLE_DENGUE)

    sql = query.build_sql()

    assert 'LEFT JOIN openalex_article oa ON oa.article_id = bp.id' in sql
    assert "COALESCE(oa.abstract, '')" in sql
    assert tools.TITLE_ABSTRACT_RANK_WEIGHTS in sql


@pytest.mark.asyncio
async def test_institution_frequency_counts_abstract_match(
    session, institution_factory, researcher_factory, article_factory
):
    institution = await institution_factory(name='Freq', acronym='FRQ')
    researcher = await researcher_factory(institution_id=institution.id)
    researcher.institution_id = institution.id  # coluna legada usada na v1
    await session.commit()
    await article_factory(
        researcher, 'Estudo regional', abstract='Surto de dengue.'
    )

    rows = await InstitutionFrequencyQuery(
        session, 'dengue', None, 'ARTICLE'
    ).execute()

    assert [(row['institution'], row['qtd']) for row in rows] == [('Freq', 1)]
