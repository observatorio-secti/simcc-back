import json
from unittest.mock import AsyncMock

import pytest

from simcc import app
from simcc.v1.ai.dependencies import get_ai_search_service


@pytest.mark.integration
def test_chat_ask_contract_preservation(client):
    mock_search = AsyncMock()
    mock_search.search_researchers_hybrid.return_value = [
        {
            'id': 'res-1',
            'name': 'Dr. Teste',
            'institution_acronym': 'UFBA',
            'institution': 'Universidade Federal da Bahia',
            'lattes_id': '123456789',
            'abstract': 'Resumo do pesquisador',
            'semantic_content': 'Conteúdo semântico de IA',
        }
    ]
    app.dependency_overrides[get_ai_search_service] = lambda: mock_search

    try:
        response = client.post(
            '/ai/chat/ask',
            json={
                'query': 'Pesquisadores de IA na UFBA',
                'session_id': 'sess_1',
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Validação estrita dos contratos com o frontend
        assert 'answer' in data
        assert 'intent' in data
        assert 'filters_extracted' in data
        assert 'researchers' in data
        assert 'productions' in data
        assert 'sources' in data
        assert isinstance(data['researchers'], list)
        assert len(data['researchers']) == 1
        assert data['researchers'][0]['name'] == 'Dr. Teste'
    finally:
        app.dependency_overrides.pop(get_ai_search_service, None)


@pytest.mark.integration
def test_chat_stream_contract_preservation(client):
    mock_search = AsyncMock()
    mock_search.search_researchers_hybrid.return_value = []
    app.dependency_overrides[get_ai_search_service] = lambda: mock_search

    try:
        response = client.post(
            '/ai/chat/ask/stream',
            json={
                'query': 'Pesquisador inexistente',
                'session_id': 'sess_stream_1',
            },
        )
        assert response.status_code == 200
        assert 'text/event-stream' in response.headers['content-type']

        lines = [
            line if isinstance(line, str) else line.decode('utf-8')
            for line in response.iter_lines()
            if line
        ]
        assert len(lines) >= 3

        events = []
        for line in lines:
            if line.startswith('data: '):
                events.append(json.loads(line.replace('data: ', '')))

        types = [e['type'] for e in events]
        assert 'metadata' in types
        assert 'delta' in types
        assert 'done' in types
    finally:
        app.dependency_overrides.pop(get_ai_search_service, None)
