from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.ai.providers.base import EmbeddingsProvider
from simcc.core.db.models.ai import (
    SearchDocumentProduction,
    SearchDocumentResearcher,
)
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.production import (
    BibliographicProduction,
    BibliographicProductionArticle,
    BibliographicProductionBook,
    BibliographicProductionBookChapter,
    Patent,
    ResearchReport,
    Software,
)
from simcc.core.db.models.researcher import Researcher


class AISearchService:
    def __init__(
        self,
        embeddings_provider: EmbeddingsProvider,
        cosine_distance_threshold: float = 0.65,
    ):
        self.embeddings = embeddings_provider
        self.cosine_distance_threshold = cosine_distance_threshold

    async def search_researchers_hybrid(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Realiza uma busca híbrida por pesquisadores combinando:
        - Filtros exatos/parciais de instituições (siglas e nomes)
        - Busca por nome próprio do pesquisador
        - Similaridade semântica vetorial (pgvector cosine_distance)
        - Linha de corte de relevância (cosine_distance <= threshold)
        """
        filters = filters or {}

        # 1. Base query
        stmt = (
            select(SearchDocumentResearcher, Researcher, Institution)
            .join(
                Researcher,
                Researcher.id == SearchDocumentResearcher.researcher_id,
            )
            .outerjoin(
                Institution, Institution.id == Researcher.institution_id
            )
        )

        # 2. Filtro por Instituições (suporta lista de siglas/nomes: UFBA, UNEB, etc)
        institutions = filters.get('institutions', [])
        if isinstance(institutions, str):
            institutions = [institutions]

        if institutions:
            inst_conditions = []
            for inst in institutions:
                inst_clean = inst.strip()
                if inst_clean:
                    inst_conditions.append(
                        Institution.acronym.ilike(f'%{inst_clean}%')
                    )
                    inst_conditions.append(
                        Institution.name.ilike(f'%{inst_clean}%')
                    )
            if inst_conditions:
                stmt = stmt.filter(or_(*inst_conditions))

        # 3. Filtro por Nome ou IDs do Pesquisador (se especificado)
        researcher_ids = filters.get('researcher_ids')
        if researcher_ids:
            stmt = stmt.filter(Researcher.id.in_(researcher_ids))
        else:
            researcher_name = filters.get('researcher_name')
            if researcher_name:
                tokens = [t.strip() for t in researcher_name.split() if t.strip()]
                for tok in tokens:
                    stmt = stmt.filter(Researcher.name.ilike(f'%{tok}%'))

        # 4. Ordenação e Busca Semântica com Linha de Corte
        if query and query.strip():
            vector = await self.embeddings.get_embeddings(query.strip())
            dist_expr = SearchDocumentResearcher.embedding.cosine_distance(
                vector
            )
            stmt = stmt.filter(dist_expr <= self.cosine_distance_threshold)
            stmt = stmt.order_by(dist_expr)
        else:
            stmt = stmt.order_by(Researcher.name.asc())

        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        rows = result.all()

        # 5. Mapear e retornar
        response = []
        for doc, researcher, institution in rows:
            response.append({
                'id': str(researcher.id),
                'name': researcher.name,
                'institution': institution.name if institution else None,
                'institution_acronym': institution.acronym
                if institution
                else None,
                'lattes_id': researcher.lattes_id,
                'abstract': researcher.abstract or researcher.abstract_ai,
                'semantic_content': doc.document_content,
            })

        return response

    async def search_productions_hybrid(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Realiza uma busca híbrida por produções científicas combinando:
        - Filtros por tipo de produção
        - Filtros temporais
        - Similaridade semântica vetorial (pgvector cosine_distance)
        - Linha de corte de relevância (cosine_distance <= threshold)
        """
        filters = filters or {}

        stmt = select(SearchDocumentProduction)

        # Filtro de tipo de produção
        production_types = filters.get('production_types')
        if production_types:
            if isinstance(production_types, str):
                production_types = [production_types]
            stmt = stmt.filter(
                SearchDocumentProduction.type.in_(production_types)
            )

        # Filtro por pesquisadores vinculados
        researcher_ids = filters.get('researcher_ids')
        if researcher_ids:
            bp_sub = select(BibliographicProduction.id).filter(
                BibliographicProduction.researcher_id.in_(researcher_ids)
            )
            pat_sub = select(Patent.id).filter(
                Patent.researcher_id.in_(researcher_ids)
            )
            soft_sub = select(Software.id).filter(
                Software.researcher_id.in_(researcher_ids)
            )
            rep_sub = select(ResearchReport.id).filter(
                ResearchReport.researcher_id.in_(researcher_ids)
            )
            stmt = stmt.filter(
                SearchDocumentProduction.production_id.in_(
                    bp_sub.union_all(pat_sub, soft_sub, rep_sub)
                )
            )

        if query and query.strip():
            vector = await self.embeddings.get_embeddings(query.strip())
            dist_expr = SearchDocumentProduction.embedding.cosine_distance(
                vector
            )
            stmt = stmt.filter(dist_expr <= self.cosine_distance_threshold)
            stmt = stmt.order_by(dist_expr)
        else:
            stmt = stmt.order_by(
                SearchDocumentProduction.last_indexed_at.desc()
            )

        stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        docs = result.scalars().all()

        response = []
        for doc in docs:
            prod_info = {
                'id': str(doc.production_id),
                'type': doc.type,
                'semantic_content': doc.document_content,
                'title': '',
                'year': None,
                'authors': '',
                'doi': None,
                'details': {},
                'researcher': {
                    'name': 'Pesquisador',
                    'institution': 'Bahia',
                },
            }

            # Enriquecimento com metadados específicos da tabela de origem
            if doc.type in ['ARTICLE', 'BOOK', 'BOOK_CHAPTER']:
                bp_res = await session.execute(
                    select(BibliographicProduction, Researcher, Institution)
                    .join(
                        Researcher,
                        Researcher.id == BibliographicProduction.researcher_id,
                    )
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                    .filter(BibliographicProduction.id == doc.production_id)
                )
                bp_row = bp_res.first()
                if bp_row:
                    bp, r, inst = bp_row
                    prod_info['title'] = bp.title
                    prod_info['year'] = bp.year or (
                        str(bp.year_) if bp.year_ else None
                    )
                    prod_info['authors'] = bp.authors or r.name
                    prod_info['doi'] = bp.doi
                    prod_info['researcher'] = {
                        'id': str(r.id),
                        'name': r.name,
                        'institution': inst.acronym or inst.name
                        if inst
                        else 'Não informada',
                    }

                    if doc.type == 'ARTICLE':
                        art = (
                            await session.execute(
                                select(BibliographicProductionArticle).filter(
                                    BibliographicProductionArticle.bibliographic_production_id
                                    == bp.id
                                )
                            )
                        ).scalars().first()
                        if art:
                            prod_info['details'] = {
                                'periodical': art.periodical_magazine_name,
                                'qualis': art.qualis,
                                'jcr': art.jcr,
                                'issn': art.issn,
                            }
                    elif doc.type == 'BOOK':
                        bk = (
                            await session.execute(
                                select(BibliographicProductionBook).filter(
                                    BibliographicProductionBook.bibliographic_production_id
                                    == bp.id
                                )
                            )
                        ).scalars().first()
                        if bk:
                            prod_info['details'] = {
                                'publisher': bk.publishing_company,
                                'city': bk.publishing_company_city,
                                'isbn': bk.isbn,
                            }
                    elif doc.type == 'BOOK_CHAPTER':
                        chp = (
                            await session.execute(
                                select(
                                    BibliographicProductionBookChapter
                                ).filter(
                                    BibliographicProductionBookChapter.bibliographic_production_id
                                    == bp.id
                                )
                            )
                        ).scalars().first()
                        if chp:
                            prod_info['details'] = {
                                'book_title': chp.book_title,
                                'publisher': chp.publishing_company,
                                'organizers': chp.organizers,
                                'isbn': chp.isbn,
                            }

            elif doc.type == 'PATENT':
                pat_res = await session.execute(
                    select(Patent, Researcher, Institution)
                    .join(Researcher, Researcher.id == Patent.researcher_id)
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                    .filter(Patent.id == doc.production_id)
                )
                pat_row = pat_res.first()
                if pat_row:
                    pat, r, inst = pat_row
                    prod_info['title'] = pat.title or 'Patente'
                    prod_info['year'] = pat.development_year or (
                        pat.deposit_date[:4] if pat.deposit_date else None
                    )
                    prod_info['authors'] = r.name
                    prod_info['details'] = {
                        'code': pat.code,
                        'category': pat.category,
                        'details': pat.details,
                        'grant_date': str(pat.grant_date)
                        if pat.grant_date
                        else None,
                    }
                    prod_info['researcher'] = {
                        'id': str(r.id),
                        'name': r.name,
                        'institution': inst.acronym or inst.name
                        if inst
                        else 'Não informada',
                    }

            elif doc.type == 'SOFTWARE':
                sft_res = await session.execute(
                    select(Software, Researcher, Institution)
                    .join(Researcher, Researcher.id == Software.researcher_id)
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                    .filter(Software.id == doc.production_id)
                )
                sft_row = sft_res.first()
                if sft_row:
                    sft, r, inst = sft_row
                    prod_info['title'] = sft.title or 'Software'
                    prod_info['year'] = str(sft.year) if sft.year else None
                    prod_info['authors'] = r.name
                    prod_info['details'] = {
                        'platform': sft.platform,
                        'environment': sft.environment,
                        'goal': sft.goal,
                        'funding': sft.financing_institutionc,
                    }
                    prod_info['researcher'] = {
                        'id': str(r.id),
                        'name': r.name,
                        'institution': inst.acronym or inst.name
                        if inst
                        else 'Não informada',
                    }

            elif doc.type == 'REPORT':
                rep_res = await session.execute(
                    select(ResearchReport, Researcher, Institution)
                    .join(
                        Researcher,
                        Researcher.id == ResearchReport.researcher_id,
                    )
                    .outerjoin(
                        Institution,
                        Institution.id == Researcher.institution_id,
                    )
                    .filter(ResearchReport.id == doc.production_id)
                )
                rep_row = rep_res.first()
                if rep_row:
                    rep, r, inst = rep_row
                    prod_info['title'] = rep.title or 'Relatório Técnico'
                    prod_info['year'] = str(rep.year) if rep.year else None
                    prod_info['authors'] = r.name
                    prod_info['details'] = {
                        'project_name': rep.project_name,
                        'funding': rep.financing_institutionc,
                    }
                    prod_info['researcher'] = {
                        'id': str(r.id),
                        'name': r.name,
                        'institution': inst.acronym or inst.name
                        if inst
                        else 'Não informada',
                    }

            response.append(prod_info)

        return response
