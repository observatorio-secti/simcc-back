from unittest.mock import AsyncMock, MagicMock

import pytest

from simcc.v1.services.ai_search_service import AISearchService


@pytest.mark.unit
def test_ai_search_service_init_threshold(mock_embeddings_provider):
    service = AISearchService(
        embeddings_provider=mock_embeddings_provider,
        cosine_distance_threshold=0.60,
    )
    assert service.cosine_distance_threshold == 0.60
    assert service.embeddings == mock_embeddings_provider


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ai_search_service_search_researchers_cutoff_application(
    mock_embeddings_provider,
):
    service = AISearchService(
        embeddings_provider=mock_embeddings_provider,
        cosine_distance_threshold=0.65,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    results = await service.search_researchers_hybrid(
        session=mock_session,
        query='inteligência artificial',
        limit=5,
    )

    assert results == []
    mock_session.execute.assert_called_once()
