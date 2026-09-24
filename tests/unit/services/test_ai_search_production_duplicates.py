from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from simcc.v1.services.ai_search_service import AISearchService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_productions_hybrid_tolerates_duplicate_books(
    mock_embeddings_provider,
):
    service = AISearchService(
        embeddings_provider=mock_embeddings_provider,
        cosine_distance_threshold=0.65,
    )

    prod_id = uuid4()
    r_id = uuid4()

    mock_doc = MagicMock()
    mock_doc.production_id = prod_id
    mock_doc.type = 'BOOK'
    mock_doc.document_content = 'Livro sobre biotecnologia vegetal'

    mock_bp = MagicMock()
    mock_bp.id = prod_id
    mock_bp.title = 'Biotecnologia Aplicada'
    mock_bp.year = '2023'
    mock_bp.authors = 'Dra. Silva'
    mock_bp.doi = None

    mock_r = MagicMock()
    mock_r.id = r_id
    mock_r.name = 'Dra. Silva'

    mock_inst = MagicMock()
    mock_inst.acronym = 'UFBA'
    mock_inst.name = 'Universidade Federal da Bahia'

    mock_bk_1 = MagicMock()
    mock_bk_1.publishing_company = 'Editora UFBA'
    mock_bk_1.publishing_company_city = 'Salvador'
    mock_bk_1.isbn = '978-1111111111'

    mock_bk_2 = MagicMock()
    mock_bk_2.publishing_company = 'Editora UFBA Digital'
    mock_bk_2.publishing_company_city = 'Salvador'
    mock_bk_2.isbn = '978-2222222222'

    mock_session = AsyncMock()

    # 1. Busca dos documentos
    res_docs = MagicMock()
    res_docs.scalars.return_value.all.return_value = [mock_doc]

    # 2. Join da produção bibliográfica
    res_bp = MagicMock()
    res_bp.first.return_value = (mock_bp, mock_r, mock_inst)

    # 3. Detalhes de livro com múltiplos registros
    res_details = MagicMock()
    res_details.scalars.return_value.first.return_value = mock_bk_1

    mock_session.execute.side_effect = [res_docs, res_bp, res_details]

    results = await service.search_productions_hybrid(
        session=mock_session,
        query='biotecnologia',
        limit=5,
        filters={'production_types': ['BOOK']},
    )

    assert len(results) == 1
    assert results[0]['title'] == 'Biotecnologia Aplicada'
    assert results[0]['details']['isbn'] == '978-1111111111'
    assert results[0]['details']['publisher'] == 'Editora UFBA'
    assert results[0]['researcher']['name'] == 'Dra. Silva'
    assert results[0]['researcher']['institution'] == 'UFBA'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_productions_hybrid_tolerates_duplicate_chapters(
    mock_embeddings_provider,
):
    service = AISearchService(
        embeddings_provider=mock_embeddings_provider,
        cosine_distance_threshold=0.65,
    )

    prod_id = uuid4()
    r_id = uuid4()

    mock_doc = MagicMock()
    mock_doc.production_id = prod_id
    mock_doc.type = 'BOOK_CHAPTER'
    mock_doc.document_content = 'Capítulo sobre enzimas e fermentação'

    mock_bp = MagicMock()
    mock_bp.id = prod_id
    mock_bp.title = 'Enzimas em Biotecnologia'
    mock_bp.year = '2024'
    mock_bp.authors = 'Dr. Santos'
    mock_bp.doi = None

    mock_r = MagicMock()
    mock_r.id = r_id
    mock_r.name = 'Dr. Santos'

    mock_inst = MagicMock()
    mock_inst.acronym = 'UNEB'
    mock_inst.name = 'Universidade do Estado da Bahia'

    mock_chp_1 = MagicMock()
    mock_chp_1.book_title = 'Avanços em Biotecnologia'
    mock_chp_1.publishing_company = 'Editora UNEB'
    mock_chp_1.organizers = 'Org A'
    mock_chp_1.isbn = '978-3333333333'

    mock_session = AsyncMock()

    res_docs = MagicMock()
    res_docs.scalars.return_value.all.return_value = [mock_doc]

    res_bp = MagicMock()
    res_bp.first.return_value = (mock_bp, mock_r, mock_inst)

    res_details = MagicMock()
    res_details.scalars.return_value.first.return_value = mock_chp_1

    mock_session.execute.side_effect = [res_docs, res_bp, res_details]

    results = await service.search_productions_hybrid(
        session=mock_session,
        query='enzimas biotecnologia',
        limit=5,
        filters={'production_types': ['BOOK_CHAPTER']},
    )

    assert len(results) == 1
    assert results[0]['title'] == 'Enzimas em Biotecnologia'
    assert results[0]['details']['book_title'] == 'Avanços em Biotecnologia'
    assert results[0]['details']['isbn'] == '978-3333333333'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_productions_hybrid_tolerates_duplicate_articles(
    mock_embeddings_provider,
):
    service = AISearchService(
        embeddings_provider=mock_embeddings_provider,
        cosine_distance_threshold=0.65,
    )

    prod_id = uuid4()
    r_id = uuid4()

    mock_doc = MagicMock()
    mock_doc.production_id = prod_id
    mock_doc.type = 'ARTICLE'
    mock_doc.document_content = 'Artigo sobre vacinas'

    mock_bp = MagicMock()
    mock_bp.id = prod_id
    mock_bp.title = 'Desenvolvimento de Vacinas'
    mock_bp.year = '2022'
    mock_bp.authors = 'Dra. Lima'
    mock_bp.doi = '10.1016/test.vacinas'

    mock_r = MagicMock()
    mock_r.id = r_id
    mock_r.name = 'Dra. Lima'

    mock_inst = MagicMock()
    mock_inst.acronym = 'Fiocruz'
    mock_inst.name = 'Fiocruz Bahia'

    mock_art_1 = MagicMock()
    mock_art_1.periodical_magazine_name = 'Journal of Biotechnology'
    mock_art_1.qualis = 'A1'
    mock_art_1.jcr = '4.5'
    mock_art_1.issn = '1234-5678'

    mock_session = AsyncMock()

    res_docs = MagicMock()
    res_docs.scalars.return_value.all.return_value = [mock_doc]

    res_bp = MagicMock()
    res_bp.first.return_value = (mock_bp, mock_r, mock_inst)

    res_details = MagicMock()
    res_details.scalars.return_value.first.return_value = mock_art_1

    mock_session.execute.side_effect = [res_docs, res_bp, res_details]

    results = await service.search_productions_hybrid(
        session=mock_session,
        query='vacinas',
        limit=5,
        filters={'production_types': ['ARTICLE']},
    )

    assert len(results) == 1
    assert results[0]['title'] == 'Desenvolvimento de Vacinas'
    assert results[0]['details']['periodical'] == 'Journal of Biotechnology'
    assert results[0]['details']['qualis'] == 'A1'
