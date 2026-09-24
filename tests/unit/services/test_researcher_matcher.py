from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from simcc.v1.services.researcher_matcher import (
    ResearcherMatcher,
)


@pytest.mark.unit
def test_researcher_matcher_normalization():
    matcher = ResearcherMatcher()

    # 1. Remoção de acentos e minúsculas
    tokens = matcher.normalize_tokens('Célia Regina D’Ávila')
    assert 'celia' in tokens
    assert 'regina' in tokens

    # 2. Remoção de preposições e artigos comuns
    tokens_eduardo = matcher.normalize_tokens(
        'Eduardo Manuel de Freitas Jorge'
    )
    assert tokens_eduardo == ['eduardo', 'manuel', 'freitas', 'jorge']
    assert 'de' not in tokens_eduardo

    # 3. Caracteres especiais e pontuações
    tokens_spec = matcher.normalize_tokens('Dr. João & Maria!')
    assert tokens_spec == ['dr', 'joao', 'maria']


@pytest.mark.unit
@pytest.mark.asyncio
async def test_researcher_matcher_find_candidates_scoring():
    matcher = ResearcherMatcher()

    mock_session = AsyncMock()
    r1_id = uuid4()
    r2_id = uuid4()

    # Linhas retornadas do banco:
    # (id, name, lattes_id, inst_acronym, inst_name, sim_score)
    mock_rows = [
        (
            r1_id,
            'Eduardo Manuel de Freitas Jorge',
            '123456',
            'UNEB',
            'Universidade do Estado da Bahia',
            0.55,
        ),
        (
            r2_id,
            'Eduardo Jorge Valadares',
            '789012',
            'UFBA',
            'Universidade Federal da Bahia',
            0.50,
        ),
    ]

    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    mock_session.execute.return_value = mock_result

    candidates = await matcher.find_candidates(
        session=mock_session,
        raw_name='Eduardo Jorge',
    )

    assert len(candidates) == 2
    names = [c.name for c in candidates]
    assert 'Eduardo Manuel de Freitas Jorge' in names
    assert 'Eduardo Jorge Valadares' in names
    assert all(c.score >= 0.8 for c in candidates)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_researcher_matcher_exact_match_score():
    matcher = ResearcherMatcher()

    mock_session = AsyncMock()
    r_id = uuid4()
    mock_rows = [
        (
            r_id,
            'Jaqueline Goes de Jesus',
            '111111',
            'UFBA',
            'Universidade Federal da Bahia',
            1.0,
        )
    ]
    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    mock_session.execute.return_value = mock_result

    candidates = await matcher.find_candidates(
        session=mock_session,
        raw_name='Jaqueline Goes de Jesus',
    )

    assert len(candidates) == 1
    assert candidates[0].score == 1.0
    assert candidates[0].id == str(r_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_researcher_matcher_empty_input():
    matcher = ResearcherMatcher()
    mock_session = AsyncMock()

    candidates = await matcher.find_candidates(
        session=mock_session, raw_name=''
    )
    assert candidates == []
