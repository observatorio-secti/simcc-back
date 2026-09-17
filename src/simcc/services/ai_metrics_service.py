import logging
import time
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.core.db.models.institution import Institution
from simcc.core.db.models.openalex import OpenAlexResearcher
from simcc.core.db.models.researcher import Researcher, ResearcherProduction

logger = logging.getLogger(__name__)


class AIMetricsService:
    """Calcula agregados estatísticos, distribuição institucional e métricas de carreira para contextualização da MarIA."""

    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._shares_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._shares_cache_timestamp: float = 0.0

    async def get_researchers_career_metrics(
        self,
        session: AsyncSession,
        researcher_ids: List[Union[UUID, str]],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retorna contagens de artigos, livros, capítulos, patentes, software e dados do OpenAlex
        para a lista de pesquisadores informados.
        """
        if not researcher_ids:
            return {}

        valid_uuids: List[UUID] = []
        for rid in researcher_ids:
            if isinstance(rid, UUID):
                valid_uuids.append(rid)
            else:
                try:
                    valid_uuids.append(UUID(str(rid)))
                except (ValueError, TypeError):
                    continue

        if not valid_uuids:
            return {}

        metrics: Dict[str, Dict[str, Any]] = {}

        try:
            # 1. Tabela researcher_production
            stmt_rp = select(ResearcherProduction).filter(
                ResearcherProduction.researcher_id.in_(valid_uuids)
            )
            res_rp = await session.execute(stmt_rp)
            for rp in res_rp.scalars().all():
                rid_str = str(rp.researcher_id)
                metrics[rid_str] = {
                    'articles': rp.articles or 0,
                    'books': rp.book or 0,
                    'book_chapters': rp.book_chapters or 0,
                    'patents': rp.patent or 0,
                    'software': rp.software or 0,
                    'brand': rp.brand or 0,
                    'work_in_event': rp.work_in_event or 0,
                    'h_index': None,
                    'citations': None,
                    'works_count': None,
                    'i10_index': None,
                }

            # 2. Tabela openalex_researcher
            stmt_oa = select(OpenAlexResearcher).filter(
                OpenAlexResearcher.researcher_id.in_(valid_uuids)
            )
            res_oa = await session.execute(stmt_oa)
            for oa in res_oa.scalars().all():
                rid_str = str(oa.researcher_id)
                if rid_str not in metrics:
                    metrics[rid_str] = {
                        'articles': 0,
                        'books': 0,
                        'book_chapters': 0,
                        'patents': 0,
                        'software': 0,
                        'brand': 0,
                        'work_in_event': 0,
                    }
                metrics[rid_str]['h_index'] = oa.h_index
                metrics[rid_str]['citations'] = oa.cited_by_count
                metrics[rid_str]['works_count'] = oa.works_count
                metrics[rid_str]['i10_index'] = oa.i10_index

        except Exception as ex:
            logger.warning(
                f'Erro ao calcular métricas de carreira de pesquisadores: {ex}'
            )

        return metrics

    async def get_institution_shares(
        self,
        session: AsyncSession,
        use_cache: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Retorna o share consolidado de produção científica e tecnológica por instituição na Bahia.
        Possui cache em memória para tempo de resposta < 1ms após a primeira consulta.
        """
        now = time.time()
        if (
            use_cache
            and self._shares_cache is not None
            and (now - self._shares_cache_timestamp) < self.cache_ttl_seconds
        ):
            return self._shares_cache

        stmt = (
            select(
                Institution.acronym,
                func.coalesce(func.sum(ResearcherProduction.articles), 0).label(
                    'articles'
                ),
                func.coalesce(func.sum(ResearcherProduction.book), 0).label(
                    'books'
                ),
                func.coalesce(
                    func.sum(ResearcherProduction.book_chapters), 0
                ).label('chapters'),
                func.coalesce(
                    func.sum(ResearcherProduction.patent), 0
                ).label('patents'),
                func.coalesce(
                    func.sum(ResearcherProduction.software), 0
                ).label('software'),
                func.count(ResearcherProduction.researcher_id).label(
                    'researchers_count'
                ),
            )
            .join(
                Researcher, Researcher.id == ResearcherProduction.researcher_id
            )
            .join(Institution, Institution.id == Researcher.institution_id)
            .group_by(Institution.acronym)
            .order_by(
                func.coalesce(
                    func.sum(ResearcherProduction.articles), 0
                ).desc()
            )
        )

        shares: Dict[str, Dict[str, Any]] = {}
        grand_total = 0

        try:
            res = await session.execute(stmt)
            rows = res.all()
            for row in rows:
                acronym = row[0] or 'Outra'
                articles = int(row[1] or 0)
                books = int(row[2] or 0)
                chapters = int(row[3] or 0)
                patents = int(row[4] or 0)
                software = int(row[5] or 0)
                res_cnt = int(row[6] or 0)

                tot = articles + books + chapters + patents + software
                grand_total += tot
                shares[acronym] = {
                    'total_productions': tot,
                    'articles': articles,
                    'books': books + chapters,
                    'patents': patents,
                    'software': software,
                    'researchers': res_cnt,
                }

            for acronym, data in shares.items():
                if grand_total > 0:
                    pct = (data['total_productions'] / grand_total) * 100.0
                    data['share'] = f'{pct:.1f}%'
                else:
                    data['share'] = '0.0%'

            if use_cache and shares:
                self._shares_cache = shares
                self._shares_cache_timestamp = now

        except Exception as ex:
            logger.warning(
                f'Erro ao calcular distribuição institucional SIMCC: {ex}'
            )

        return shares

    async def get_global_search_context(
        self,
        session: AsyncSession,
        plan: Optional[Any] = None,
        sample_count: int = 0,
        matched_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Gera o pacote de contexto quantitativo global para enriquecer o prompt da MarIA
        e os metadados de UI enviados ao frontend.
        """
        shares = await self.get_institution_shares(session)
        total_matched = (
            matched_count if matched_count is not None else sample_count
        )

        filters_dict = {}
        if plan and hasattr(plan, 'filters') and plan.filters:
            if hasattr(plan.filters, 'model_dump'):
                filters_dict = plan.filters.model_dump(exclude_none=True)
            elif isinstance(plan.filters, dict):
                filters_dict = plan.filters

        return {
            'total_matched': total_matched,
            'sample_count': sample_count,
            'institution_shares': shares,
            'filters_applied': filters_dict,
            'notice': (
                f'Exibindo amostra de {sample_count} itens mais '
                f'relevantes no SIMCC. O acervo completo das '
                f'instituições baianas (como UFBA) contém '
                f'expressivamente mais produções na base.'
            ),
        }
