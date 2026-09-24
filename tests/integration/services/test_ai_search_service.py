import pytest
import pytest_asyncio
from sqlalchemy import select

from simcc.core.db.models.ai import SearchDocumentResearcher
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.researcher import Researcher
from simcc.v1.services.ai_search_service import AISearchService


@pytest_asyncio.fixture(autouse=True)
async def seed_ai_search_data(session):
    """Garante a existência de dados para busca nos testes de integração."""
    # 1. Instituição UNEB
    inst_stmt = select(Institution).filter(Institution.acronym == 'UNEB')
    res_inst = await session.execute(inst_stmt)
    inst = res_inst.scalars().first()
    if not inst:
        inst = Institution(
            name='Universidade do Estado da Bahia',
            acronym='UNEB',
        )
        session.add(inst)
        await session.commit()
        await session.refresh(inst)

    # 2. Pesquisador Eduardo Manuel
    r_stmt = select(Researcher).filter(
        Researcher.lattes_id == '1111222233334444'
    )
    res_r = await session.execute(r_stmt)
    researcher = res_r.scalars().first()
    if not researcher:
        researcher = Researcher(
            name='Eduardo Manuel De Freitas Jorge',
            lattes_id='1111222233334444',
            institution_id=inst.id,
        )
        session.add(researcher)
        await session.commit()
        await session.refresh(researcher)

    # 3. Documento de busca
    doc_stmt = select(SearchDocumentResearcher).filter(
        SearchDocumentResearcher.researcher_id == researcher.id
    )
    res_doc = await session.execute(doc_stmt)
    doc = res_doc.scalars().first()
    if not doc:
        doc = SearchDocumentResearcher(
            researcher_id=researcher.id,
            document_content='Pesquisador em tecnologia e computação na UNEB.',
            embedding=[0.01] * 1536,
        )
        session.add(doc)
        await session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_researchers_by_institution_filter(
    session, mock_embeddings_provider
):
    search_service = AISearchService(
        embeddings_provider=mock_embeddings_provider
    )

    results = await search_service.search_researchers_hybrid(
        session=session, query='', limit=10, filters={'institutions': ['UNEB']}
    )

    assert len(results) > 0
    for r in results:
        assert r['institution_acronym'] == 'UNEB' or 'Estado da Bahia' in (
            r['institution'] or ''
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_researchers_by_name_filter(
    session, mock_embeddings_provider
):
    search_service = AISearchService(
        embeddings_provider=mock_embeddings_provider
    )

    results = await search_service.search_researchers_hybrid(
        session=session,
        query='',
        limit=5,
        filters={'researcher_name': 'Eduardo Manuel'},
    )

    assert len(results) >= 1
    assert 'Eduardo Manuel De Freitas Jorge' in results[0]['name']


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_researchers_multi_institution(
    session, mock_embeddings_provider
):
    search_service = AISearchService(
        embeddings_provider=mock_embeddings_provider
    )

    results = await search_service.search_researchers_hybrid(
        session=session,
        query='tecnologia',
        limit=10,
        filters={'institutions': ['UFBA', 'UNEB']},
    )

    assert len(results) > 0
    found_acronyms = {
        r.get('institution_acronym')
        for r in results
        if r.get('institution_acronym')
    }
    assert ('UFBA' in found_acronyms) or ('UNEB' in found_acronyms)
