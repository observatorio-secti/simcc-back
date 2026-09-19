from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from simcc.services.ai_search_service import AISearchService


@pytest.fixture
def mock_embeddings():
    provider = AsyncMock()
    provider.get_embeddings.return_value = [0.1] * 1536
    return provider


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_researchers_hybrid_with_territory_and_affiliations(
    mock_embeddings,
):
    """
    Valida que search_researchers_hybrid carrega os múltiplos vínculos N:N
    e associa os territórios de identidade corretos a cada pesquisador.
    """
    service = AISearchService(embeddings_provider=mock_embeddings)
    session = AsyncMock()

    r1_id = uuid4()
    mock_doc = MagicMock()
    mock_doc.document_content = 'Pesquisador em IA e Redes Neurais'

    mock_r = MagicMock()
    mock_r.id = r1_id
    mock_r.name = 'Dr. Fulano da Silva'
    mock_r.lattes_id = '1234567890'
    mock_r.abstract = 'Resumo acadêmico'
    mock_r.abstract_ai = None

    mock_inst = MagicMock()
    mock_inst.name = 'Universidade Federal da Bahia'
    mock_inst.acronym = 'UFBA'

    # Resposta da query principal de pesquisadores
    res_main = MagicMock()
    res_main.all.return_value = [(mock_doc, mock_r, mock_inst)]

    # Resposta da batch query de vínculos N:N (researcher_institution)
    mock_aff1 = MagicMock()
    mock_aff1.researcher_id = r1_id
    mock_aff1.institution_name = 'Universidade Federal da Bahia'
    mock_aff1.institution_acronym = 'UFBA'
    mock_aff1.identity_territory = 'METROPOLITANA DE SALVADOR'
    mock_aff1.workload = 40.0
    mock_aff1.city_name = 'Salvador'

    mock_aff2 = MagicMock()
    mock_aff2.researcher_id = r1_id
    mock_aff2.institution_name = 'Universidade Estadual de Feira de Santana'
    mock_aff2.institution_acronym = 'UEFS'
    mock_aff2.identity_territory = 'PORTAL DO SERTÃO'
    mock_aff2.workload = 20.0
    mock_aff2.city_name = 'Feira de Santana'

    res_aff = MagicMock()
    res_aff.all.return_value = [mock_aff1, mock_aff2]

    session.execute.side_effect = [res_main, res_aff]

    results = await service.search_researchers_hybrid(
        session=session,
        query='inteligência artificial',
        limit=5,
        filters={'identity_territory': 'Portal do Sertão'},
    )

    assert len(results) == 1
    r_res = results[0]
    assert r_res['id'] == str(r1_id)
    assert r_res['name'] == 'Dr. Fulano da Silva'
    assert 'METROPOLITANA DE SALVADOR' in r_res['territories']
    assert 'PORTAL DO SERTÃO' in r_res['territories']
    expected_affiliations_count = 2
    assert len(r_res['affiliations']) == expected_affiliations_count
    assert r_res['affiliations'][0]['institution_acronym'] == 'UFBA'
    assert r_res['affiliations'][1]['institution_acronym'] == 'UEFS'


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_productions_hybrid_with_territory_filter(
    mock_embeddings,
):
    """
    Valida que search_productions_hybrid enriquece os metadados do autor
    com os territórios de identidade obtidos via N:N.
    """
    service = AISearchService(embeddings_provider=mock_embeddings)
    session = AsyncMock()

    prod_id, r_id = uuid4(), uuid4()

    mock_doc = MagicMock(
        production_id=prod_id,
        type='ARTICLE',
        document_content='Artigo sobre Saúde no Semiárido',
    )
    res_search = MagicMock()
    res_search.scalars.return_value.all.return_value = [mock_doc]

    res_bp = MagicMock()
    res_bp.first.return_value = (
        MagicMock(
            id=prod_id,
            title='Artigo sobre Saúde no Semiárido',
            year='2023',
            year_=2023,
            authors='Dra. Maria',
            doi='10.1000/182',
        ),
        MagicMock(id=r_id, name='Dra. Maria'),
        MagicMock(
            acronym='UEFS', name='Universidade Estadual de Feira de Santana'
        ),
    )

    res_art = MagicMock()
    res_art.scalars.return_value.first.return_value = MagicMock(
        periodical_magazine_name='Revista de Saúde',
        qualis='A1',
        jcr=None,
        issn='1234-5678',
    )

    res_author_aff = MagicMock()
    res_author_aff.all.return_value = [
        MagicMock(
            researcher_id=r_id,
            identity_territory='PORTAL DO SERTÃO',
            institution_name='Universidade Estadual de Feira de Santana',
            institution_acronym='UEFS',
        )
    ]

    session.execute.side_effect = [
        res_search,
        res_bp,
        res_art,
        res_author_aff,
    ]

    results = await service.search_productions_hybrid(
        session=session,
        query='saúde pública',
        limit=5,
        filters={'identity_territory': 'Portal do Sertão'},
    )

    assert len(results) == 1
    p_res = results[0]
    assert p_res['title'] == 'Artigo sobre Saúde no Semiárido'
    assert p_res['researcher']['id'] == str(r_id)
    assert p_res['researcher']['territories'] == ['PORTAL DO SERTÃO']
