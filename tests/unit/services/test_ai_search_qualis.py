from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from simcc.ai.query_planner import SearchFilters
from simcc.services.ai_search_service import AISearchService
from simcc.services.maria_service import MariaService


@pytest.fixture
def mock_embeddings():
    provider = AsyncMock()
    provider.get_embeddings.return_value = [0.1] * 1536
    return provider


def _create_mock_article(prod_id, r_id, title, qualis):
    doc = MagicMock(
        production_id=prod_id,
        type='ARTICLE',
        document_content=title,
    )
    bp = MagicMock(
        id=prod_id,
        title=title,
        year='2023',
        authors='Dr. Silva',
        doi='10.1000/1',
    )
    r = MagicMock(id=r_id, name='Dr. Silva')
    inst = MagicMock(acronym='UFBA', name='Universidade Federal da Bahia')
    res_bp = MagicMock()
    res_bp.first.return_value = (bp, r, inst)

    res_art = MagicMock()
    res_art.scalars.return_value.first.return_value = MagicMock(
        periodical_magazine_name='Revista', qualis=qualis
    )
    return doc, res_bp, res_art


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_productions_hybrid_with_multi_qualis(mock_embeddings):
    """
    Valida que search_productions_hybrid filtra produções que contenham
    qualquer um dos estratos Qualis informados (ex: ['A1', 'A2']).
    """
    service = AISearchService(embeddings_provider=mock_embeddings)
    session = AsyncMock()
    r_id = uuid4()

    b1 = _create_mock_article(uuid4(), r_id, 'Artigo A1', 'A1')
    b2 = _create_mock_article(uuid4(), r_id, 'Artigo B1', 'B1')
    b3 = _create_mock_article(uuid4(), r_id, 'Artigo A2', 'A2')

    res_search = MagicMock()
    res_search.scalars.return_value.all.return_value = [b1[0], b2[0], b3[0]]

    session.execute.side_effect = [
        res_search,
        b1[1],
        b1[2],
        b2[1],
        b2[2],
        b3[1],
        b3[2],
        MagicMock(all=MagicMock(return_value=[])),
    ]

    results = await service.search_productions_hybrid(
        session=session,
        query='inteligência artificial',
        limit=10,
        filters={'qualis': ['A1', 'A2']},
    )

    expected_matched_articles = 2
    assert len(results) == expected_matched_articles
    qualis_results = [r['details']['qualis'] for r in results]
    assert 'A1' in qualis_results
    assert 'A2' in qualis_results
    assert 'B1' not in qualis_results


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_researchers_hybrid_with_qualis_filter(mock_embeddings):
    """
    Valida que search_researchers_hybrid aceita filtro por Qualis.
    """
    service = AISearchService(embeddings_provider=mock_embeddings)
    session = AsyncMock()

    r1_id = uuid4()
    mock_doc = MagicMock(document_content='Pesquisador A1')
    mock_r = MagicMock(
        id=r1_id,
        lattes_id='111',
        abstract='Resumo',
        abstract_ai=None,
    )
    mock_r.name = 'Dra. Cientista'
    mock_inst = MagicMock(acronym='UFBA')
    mock_inst.name = 'UFBA'

    res_main = MagicMock()
    res_main.all.return_value = [(mock_doc, mock_r, mock_inst)]
    res_aff = MagicMock()
    res_aff.all.return_value = []

    session.execute.side_effect = [res_main, res_aff]

    results = await service.search_researchers_hybrid(
        session=session,
        query='biotecnologia',
        limit=5,
        filters={'qualis': ['A1']},
    )

    assert len(results) == 1
    assert results[0]['name'] == 'Dra. Cientista'


@pytest.mark.unit
def test_build_ui_filters_includes_qualis():
    """Valida que _build_ui_filters inclui a lista de Qualis nos metadados."""
    filters = SearchFilters(
        institutions=['UFBA'],
        qualis=['A1', 'A2'],
        identity_territory='Metropolitana de Salvador',
    )
    ui_filters = MariaService._build_ui_filters(filters)

    assert 'qualis' in ui_filters
    assert ui_filters['qualis'] == ['A1', 'A2']
    assert ui_filters['identity_territory'] == 'Metropolitana de Salvador'
