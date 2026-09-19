from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from simcc.ai.providers.base import EmbeddingsProvider
from simcc.core.db.models.ai import (
    SearchDocumentProduction,
    SearchDocumentResearcher,
)
from simcc.core.db.models.institution import Institution
from simcc.core.db.models.location import City
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
from simcc.core.db.models.researcher_institution import ResearcherInstitution


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

        # 4. Filtro por Território de Identidade (N:N em researcher_institution)
        identity_territory = filters.get('identity_territory')
        if identity_territory:
            clean_terr = identity_territory.strip()
            if clean_terr:
                terr_sub = (
                    select(ResearcherInstitution.researcher_id)
                    .filter(
                        ResearcherInstitution.identity_territory.ilike(
                            f'%{clean_terr}%'
                        )
                    )
                    .distinct()
                )
                stmt = stmt.filter(Researcher.id.in_(terr_sub))

        # 5. Ordenação e Busca Semântica com Linha de Corte
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

        # 6. Carregar em lote vínculos N:N (researcher_institution)
        r_ids = [researcher.id for _, researcher, _ in rows if hasattr(researcher, 'id')]
        affiliations_by_rid: Dict[str, List[Dict[str, Any]]] = {}
        if r_ids:
            try:
                stmt_aff = (
                    select(
                        ResearcherInstitution.researcher_id,
                        ResearcherInstitution.identity_territory,
                        ResearcherInstitution.workload,
                        Institution.name.label('institution_name'),
                        Institution.acronym.label('institution_acronym'),
                        City.name.label('city_name'),
                    )
                    .join(
                        Institution,
                        Institution.id == ResearcherInstitution.institution_id,
                    )
                    .outerjoin(City, City.id == ResearcherInstitution.city_id)
                    .filter(ResearcherInstitution.researcher_id.in_(r_ids))
                )
                res_aff = await session.execute(stmt_aff)
                for aff in res_aff.all():
                    rid_str = str(aff.researcher_id)
                    if rid_str not in affiliations_by_rid:
                        affiliations_by_rid[rid_str] = []
                    affiliations_by_rid[rid_str].append({
                        'institution': aff.institution_name,
                        'institution_acronym': aff.institution_acronym,
                        'identity_territory': aff.identity_territory,
                        'workload': float(aff.workload)
                        if aff.workload is not None
                        else None,
                        'city': aff.city_name,
                    })
            except Exception:
                pass

        # 7. Mapear e retornar
        response = []
        for doc, researcher, institution in rows:
            rid_str = str(researcher.id)
            affs = affiliations_by_rid.get(rid_str, [])
            territories = sorted(list({
                a['identity_territory']
                for a in affs
                if a.get('identity_territory')
            }))
            response.append({
                'id': rid_str,
                'name': researcher.name,
                'institution': institution.name if institution else None,
                'institution_acronym': institution.acronym
                if institution
                else None,
                'lattes_id': researcher.lattes_id,
                'abstract': researcher.abstract or researcher.abstract_ai,
                'semantic_content': doc.document_content,
                'territories': territories,
                'affiliations': affs,
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

        # Filtro por Território de Identidade (N:N em researcher_institution)
        identity_territory = filters.get('identity_territory')
        if identity_territory:
            clean_terr = identity_territory.strip()
            if clean_terr:
                rids_sub = (
                    select(ResearcherInstitution.researcher_id)
                    .filter(
                        ResearcherInstitution.identity_territory.ilike(
                            f'%{clean_terr}%'
                        )
                    )
                    .distinct()
                )
                bp_sub_terr = select(BibliographicProduction.id).filter(
                    BibliographicProduction.researcher_id.in_(rids_sub)
                )
                pat_sub_terr = select(Patent.id).filter(
                    Patent.researcher_id.in_(rids_sub)
                )
                soft_sub_terr = select(Software.id).filter(
                    Software.researcher_id.in_(rids_sub)
                )
                rep_sub_terr = select(ResearchReport.id).filter(
                    ResearchReport.researcher_id.in_(rids_sub)
                )
                stmt = stmt.filter(
                    SearchDocumentProduction.production_id.in_(
                        bp_sub_terr.union_all(
                            pat_sub_terr, soft_sub_terr, rep_sub_terr
                        )
                    )
                )

        # Filtro temporal (year_from e year_to)
        year_from = filters.get('year_from')
        year_to = filters.get('year_to')
        if year_from is not None or year_to is not None:
            bp_temp_conds = []
            pat_temp_conds = []
            soft_temp_conds = []
            rep_temp_conds = []

            if year_from is not None:
                bp_temp_conds.append(
                    or_(
                        BibliographicProduction.year_ >= year_from,
                        BibliographicProduction.year >= str(year_from),
                    )
                )
                pat_temp_conds.append(
                    or_(
                        Patent.development_year >= str(year_from),
                        Patent.deposit_date >= str(year_from),
                    )
                )
                soft_temp_conds.append(Software.year >= year_from)
                rep_temp_conds.append(ResearchReport.year >= year_from)

            if year_to is not None:
                bp_temp_conds.append(
                    or_(
                        BibliographicProduction.year_ <= year_to,
                        BibliographicProduction.year <= str(year_to),
                    )
                )
                pat_temp_conds.append(
                    or_(
                        Patent.development_year <= str(year_to),
                        Patent.deposit_date <= str(year_to),
                    )
                )
                soft_temp_conds.append(Software.year <= year_to)
                rep_temp_conds.append(ResearchReport.year <= year_to)

            bp_sub_temp = select(BibliographicProduction.id).filter(
                and_(*bp_temp_conds)
            )
            pat_sub_temp = select(Patent.id).filter(and_(*pat_temp_conds))
            soft_sub_temp = select(Software.id).filter(and_(*soft_temp_conds))
            rep_sub_temp = select(ResearchReport.id).filter(
                and_(*rep_temp_conds)
            )

            valid_temporal_ids = bp_sub_temp.union_all(
                pat_sub_temp, soft_sub_temp, rep_sub_temp
            )
            stmt = stmt.filter(
                SearchDocumentProduction.production_id.in_(valid_temporal_ids)
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

            # Validação defensiva de ano (compatibilidade unitária e banco)
            if year_from is not None or year_to is not None:
                pyear = prod_info.get('year')
                if not pyear:
                    continue
                try:
                    pyear_int = int(str(pyear)[:4])
                    if year_from is not None and pyear_int < year_from:
                        continue
                    if year_to is not None and pyear_int > year_to:
                        continue
                except (ValueError, TypeError):
                    continue

            response.append(prod_info)
            if len(response) >= limit:
                break

        # Enriquecer pesquisadores das produções com vínculos e territórios
        unique_author_rids = []
        for p in response:
            r_info = p.get('researcher')
            if r_info and r_info.get('id'):
                try:
                    from uuid import UUID
                    unique_author_rids.append(UUID(str(r_info['id'])))
                except (ValueError, TypeError):
                    pass

        if unique_author_rids:
            try:
                stmt_author_aff = (
                    select(
                        ResearcherInstitution.researcher_id,
                        ResearcherInstitution.identity_territory,
                        Institution.name.label('institution_name'),
                        Institution.acronym.label('institution_acronym'),
                    )
                    .join(
                        Institution,
                        Institution.id == ResearcherInstitution.institution_id,
                    )
                    .filter(
                        ResearcherInstitution.researcher_id.in_(
                            list(set(unique_author_rids))
                        )
                    )
                )
                res_author_aff = await session.execute(stmt_author_aff)
                author_territories_by_rid: Dict[str, List[str]] = {}
                for row in res_author_aff.all():
                    rid_s = str(row.researcher_id)
                    if rid_s not in author_territories_by_rid:
                        author_territories_by_rid[rid_s] = []
                    if (
                        row.identity_territory
                        and row.identity_territory
                        not in author_territories_by_rid[rid_s]
                    ):
                        author_territories_by_rid[rid_s].append(
                            row.identity_territory
                        )

                for p in response:
                    r_info = p.get('researcher')
                    if r_info and r_info.get('id'):
                        rid_s = str(r_info['id'])
                        r_info['territories'] = author_territories_by_rid.get(
                            rid_s, []
                        )
            except Exception:
                pass

        return response
