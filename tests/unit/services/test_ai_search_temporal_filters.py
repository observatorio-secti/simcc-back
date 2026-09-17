from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from simcc.ai.query_planner import QueryPlan, SearchFilters
from simcc.services.ai_search_service import AISearchService
from simcc.services.maria_service import MariaService

YEAR_2018 = 2018
YEAR_2019 = 2019
YEAR_2020 = 2020
YEAR_2021 = 2021
YEAR_2022 = 2022
YEAR_2023 = 2023
YEAR_2024 = 2024
YEAR_2025 = 2025


def _create_mock_production_chain(
    prod_id, prod_type, title, year, researcher_name
):
    mock_doc = MagicMock()
    mock_doc.production_id = prod_id
    mock_doc.type = prod_type
    mock_doc.document_content = f'{title} ({year})'

    mock_bp = MagicMock()
    mock_bp.id = prod_id
    mock_bp.title = title
    mock_bp.year = str(year)
    mock_bp.year_ = int(year)
    mock_bp.authors = researcher_name
    mock_bp.doi = None

    mock_r = MagicMock()
    mock_r.id = uuid4()
    mock_r.name = researcher_name

    mock_inst = MagicMock()
    mock_inst.acronym = 'UFBA'
    mock_inst.name = 'Universidade Federal da Bahia'

    mock_art = MagicMock()
    mock_art.periodical_magazine_name = 'Journal of Science'
    mock_art.qualis = 'A1'
    mock_art.jcr = None
    mock_art.issn = None

    return mock_doc, mock_bp, mock_r, mock_inst, mock_art


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_productions_hybrid_filters_year_from(
    mock_embeddings_provider,
):
    """
    Valida se search_productions_hybrid descarta produções
    anteriores a year_from.
    """
    service = AISearchService(
        embeddings_provider=mock_embeddings_provider,
        cosine_distance_threshold=0.65,
    )

    items = [
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 1', YEAR_2020, 'Dr. A'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 2', YEAR_2021, 'Dr. B'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 3', YEAR_2023, 'Dr. C'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 4', YEAR_2024, 'Dr. D'
        ),
    ]

    docs = [item[0] for item in items]

    mock_session = AsyncMock()
    res_docs = MagicMock()
    res_docs.scalars.return_value.all.return_value = docs

    side_effects = [res_docs]
    for _, bp, r, inst, art in items:
        res_bp = MagicMock()
        res_bp.first.return_value = (bp, r, inst)
        res_detail = MagicMock()
        res_detail.scalars.return_value.first.return_value = art
        side_effects.extend([res_bp, res_detail])

    mock_session.execute.side_effect = side_effects

    results = await service.search_productions_hybrid(
        session=mock_session,
        query='saúde pública',
        limit=10,
        filters={'year_from': YEAR_2023},
    )

    assert len(results) > 0, 'Deveria retornar produções elegíveis'
    for prod in results:
        assert prod.get('year') is not None
        assert int(prod['year']) >= YEAR_2023


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_productions_hybrid_filters_year_to(
    mock_embeddings_provider,
):
    """
    Valida se search_productions_hybrid descarta produções
    posteriores a year_to.
    """
    service = AISearchService(
        embeddings_provider=mock_embeddings_provider,
        cosine_distance_threshold=0.65,
    )

    items = [
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Histórico 1', YEAR_2018, 'Dr. A'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Histórico 2', YEAR_2019, 'Dr. B'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Futuro 1', YEAR_2021, 'Dr. C'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Futuro 2', YEAR_2024, 'Dr. D'
        ),
    ]

    docs = [item[0] for item in items]

    mock_session = AsyncMock()
    res_docs = MagicMock()
    res_docs.scalars.return_value.all.return_value = docs

    side_effects = [res_docs]
    for _, bp, r, inst, art in items:
        res_bp = MagicMock()
        res_bp.first.return_value = (bp, r, inst)
        res_detail = MagicMock()
        res_detail.scalars.return_value.first.return_value = art
        side_effects.extend([res_bp, res_detail])

    mock_session.execute.side_effect = side_effects

    results = await service.search_productions_hybrid(
        session=mock_session,
        query='história da saúde',
        limit=10,
        filters={'year_to': YEAR_2020},
    )

    assert len(results) > 0, 'Deveria retornar produções elegíveis'
    for prod in results:
        assert prod.get('year') is not None
        assert int(prod['year']) <= YEAR_2020


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_productions_hybrid_filters_year_range(
    mock_embeddings_provider,
):
    """
    Valida se search_productions_hybrid filtra estritamente [2021, 2023].
    """
    service = AISearchService(
        embeddings_provider=mock_embeddings_provider,
        cosine_distance_threshold=0.65,
    )

    items = [
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 2019', YEAR_2019, 'Dr. A'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 2021', YEAR_2021, 'Dr. B'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 2022', YEAR_2022, 'Dr. C'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 2023', YEAR_2023, 'Dr. D'
        ),
        _create_mock_production_chain(
            uuid4(), 'ARTICLE', 'Artigo 2025', YEAR_2025, 'Dr. E'
        ),
    ]

    docs = [item[0] for item in items]

    mock_session = AsyncMock()
    res_docs = MagicMock()
    res_docs.scalars.return_value.all.return_value = docs

    side_effects = [res_docs]
    for _, bp, r, inst, art in items:
        res_bp = MagicMock()
        res_bp.first.return_value = (bp, r, inst)
        res_detail = MagicMock()
        res_detail.scalars.return_value.first.return_value = art
        side_effects.extend([res_bp, res_detail])

    mock_session.execute.side_effect = side_effects

    results = await service.search_productions_hybrid(
        session=mock_session,
        query='epidemiologia',
        limit=10,
        filters={'year_from': YEAR_2021, 'year_to': YEAR_2023},
    )

    assert len(results) > 0, 'Deveria retornar produções elegíveis'
    for prod in results:
        assert prod.get('year') is not None
        ano = int(prod['year'])
        assert YEAR_2021 <= ano <= YEAR_2023


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maria_chat_ask_respects_temporal_filters(
    mock_llm_provider, mock_embeddings_provider
):
    """
    Valida o fluxo completo no MariaService.chat_ask com recorte temporal.
    """
    service = MariaService(
        llm=mock_llm_provider, embeddings=mock_embeddings_provider
    )

    planner = AsyncMock()
    planner.plan.return_value = QueryPlan(
        intent='production_search',
        semantic_query='dengue',
        filters=SearchFilters(
            production_types=['ARTICLE'],
            year_from=YEAR_2023,
        ),
    )

    search_service = AsyncMock()
    search_service.search_productions_hybrid.return_value = [
        {
            'id': 'p-old',
            'type': 'ARTICLE',
            'title': 'Dengue 2018',
            'year': str(YEAR_2018),
            'authors': 'Autor A',
            'doi': None,
            'details': {},
            'researcher': {'name': 'Autor A', 'institution': 'UFBA'},
        },
        {
            'id': 'p-new',
            'type': 'ARTICLE',
            'title': 'Dengue 2024',
            'year': str(YEAR_2024),
            'authors': 'Autor B',
            'doi': None,
            'details': {},
            'researcher': {'name': 'Autor B', 'institution': 'UFBA'},
        },
    ]

    session = AsyncMock()

    response = await service.chat_ask(
        session=session,
        query='Artigos sobre dengue a partir de 2023',
        planner=planner,
        search_service=search_service,
    )

    expected_filters = {
        'institutions': [],
        'production_types': ['ARTICLE'],
        'year_from': YEAR_2023,
    }
    search_service.search_productions_hybrid.assert_called_once_with(
        session=session,
        query='dengue',
        limit=10,
        filters=expected_filters,
    )

    for p in response.productions:
        if p.get('year'):
            assert int(p['year']) >= YEAR_2023
