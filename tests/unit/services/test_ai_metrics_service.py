from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from simcc.core.db.models.openalex import OpenAlexResearcher
from simcc.core.db.models.researcher import ResearcherProduction
from simcc.services.ai_metrics_service import AIMetricsService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_researchers_career_metrics_empty():
    service = AIMetricsService()
    session = AsyncMock()

    assert await service.get_researchers_career_metrics(session, []) == {}
    assert (
        await service.get_researchers_career_metrics(
            session, ['invalid-uuid-string']
        )
        == {}
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_researchers_career_metrics_success():
    service = AIMetricsService()
    session = AsyncMock()

    r1_id = uuid4()
    r2_id = uuid4()

    mock_rp = ResearcherProduction(
        researcher_id=r1_id,
        articles=42,
        book=2,
        book_chapters=5,
        patent=3,
        software=1,
        brand=0,
        work_in_event=10,
    )

    mock_oa = OpenAlexResearcher(
        researcher_id=r1_id,
        h_index=15,
        cited_by_count=650,
        works_count=45,
        i10_index=12,
    )

    res_rp = MagicMock()
    res_rp.scalars.return_value.all.return_value = [mock_rp]

    res_oa = MagicMock()
    res_oa.scalars.return_value.all.return_value = [mock_oa]

    session.execute.side_effect = [res_rp, res_oa]

    metrics = await service.get_researchers_career_metrics(
        session, [str(r1_id), str(r2_id)]
    )

    assert str(r1_id) in metrics
    assert metrics[str(r1_id)]['articles'] == 42
    assert metrics[str(r1_id)]['books'] == 2
    assert metrics[str(r1_id)]['patents'] == 3
    assert metrics[str(r1_id)]['h_index'] == 15
    assert metrics[str(r1_id)]['citations'] == 650


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_institution_shares_and_cache():
    service = AIMetricsService(cache_ttl_seconds=3600)
    session = AsyncMock()

    # acronym, articles, books, chapters, patents, software, researchers_count
    mock_rows = [
        ('UFBA', 800, 50, 50, 40, 10, 120),  # total = 950
        ('UNEB', 50, 0, 0, 0, 0, 30),  # total = 50
    ]
    res = MagicMock()
    res.all.return_value = mock_rows
    session.execute.return_value = res

    shares = await service.get_institution_shares(session, use_cache=True)

    assert 'UFBA' in shares
    assert 'UNEB' in shares
    assert shares['UFBA']['total_productions'] == 950
    assert shares['UFBA']['share'] == '95.0%'
    assert shares['UNEB']['total_productions'] == 50
    assert shares['UNEB']['share'] == '5.0%'

    # Second call should use in-memory cache
    session.execute.reset_mock()
    cached_shares = await service.get_institution_shares(
        session, use_cache=True
    )
    assert cached_shares == shares
    session.execute.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_global_search_context():
    service = AIMetricsService()
    session = AsyncMock()

    res = MagicMock()
    res.all.return_value = [('UFBA', 100, 10, 10, 5, 5, 20)]
    session.execute.return_value = res

    context = await service.get_global_search_context(
        session=session,
        plan=None,
        sample_count=10,
        matched_count=150,
    )

    assert context['total_matched'] == 150
    assert context['sample_count'] == 10
    assert 'UFBA' in context['institution_shares']
    assert 'notice' in context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_territory_summary_success():
    service = AIMetricsService()
    session = AsyncMock()

    # 1. Total pesquisadores (count scalar)
    res_r = MagicMock()
    res_r.scalar.return_value = 45

    # 2. Instituições (all)
    res_inst = MagicMock()
    res_inst.all.return_value = [('UEFS',), ('IFBA',)]

    # 3. Produções agregadas (first row)
    res_prod = MagicMock()
    res_prod.first.return_value = (350, 20, 30, 10, 5)

    session.execute.side_effect = [res_r, res_inst, res_prod]

    summary = await service.get_territory_summary(session, 'Portal do Sertão')

    assert summary['territory'] == 'Portal do Sertão'
    assert summary['researchers_count'] == 45
    assert summary['institutions'] == ['UEFS', 'IFBA']
    assert summary['articles'] == 350
    assert summary['total_productions'] == 415
    assert summary['patents'] == 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_global_search_context_with_territory():
    service = AIMetricsService()
    session = AsyncMock()

    # Mocks para get_institution_shares
    res_shares = MagicMock()
    res_shares.all.return_value = [('UEFS', 200, 10, 10, 5, 5, 30)]

    # Mocks para get_territory_summary
    res_r = MagicMock()
    res_r.scalar.return_value = 25
    res_inst = MagicMock()
    res_inst.all.return_value = [('UEFS',)]
    res_prod = MagicMock()
    res_prod.first.return_value = (150, 5, 5, 2, 1)

    session.execute.side_effect = [res_shares, res_r, res_inst, res_prod]

    plan_mock = MagicMock()
    plan_mock.filters.model_dump.return_value = {
        'identity_territory': 'Portal do Sertão'
    }

    context = await service.get_global_search_context(
        session=session,
        plan=plan_mock,
        sample_count=5,
        matched_count=25,
    )

    assert 'territory_summary' in context
    assert context['territory_summary']['territory'] == 'Portal do Sertão'
    assert context['territory_summary']['researchers_count'] == 25
    assert 'Portal do Sertão' in context['notice']
