from simcc.queries.base import BaseQuery
from simcc.repositories import tools


class BaseProductionQuery(BaseQuery):
    SUPPORTED_FILTERS = {
        'institution_id',
        'graduate_program_id',
        'researcher_id',
        'dep_id',
        'group_id',
        'lattes_id',
        'term',
        'terms',
        'institution',
        'graduate_program',
        'departament',
        'group',
        'city',
        'area',
        'modality',
        'graduation',
        'year',
        'type',
        'distinct',
        'collection_id',
        'star',
    }

    def __init__(
        self,
        session,
        table_alias: str,
        year_col: str = 'year',
        researcher_id_col: str = 'researcher_id',
        distinct_col: str = 'title',
    ):
        super().__init__(session)
        self.table_alias = table_alias
        self.year_col = year_col
        self.researcher_id_col = researcher_id_col
        self.distinct_col = distinct_col
        self.term_value = None
        self.year_value = None
        self.distinct_value = None
        self.type_value = None

        # Default joins
        self.joins = {
            'researcher': f'LEFT JOIN researcher r ON r.id = {self.table_alias}.{self.researcher_id_col}',
        }

    def _apply_term_filter(self, value):
        self.term_value = value

    def _apply_terms_filter(self, value):
        self.term_value = value

    def _apply_year_filter(self, value):
        self.year_value = int(value)

    def _apply_type_filter(self, value):
        self.type_value = value

    def _apply_distinct_filter(self, value):
        self.distinct_value = value

    def _apply_star_filter(self, value):
        if value:
            self.params['star_ids'] = (
                value if isinstance(value, list) else [value]
            )
            self.filters_sql.append(
                f' AND {self.table_alias}.id = ANY(:star_ids)'
            )

    def _apply_collection_id_filter(self, value):
        self.params['collection_id'] = (
            value if isinstance(value, list) else [value]
        )
        self.filters_sql.append(
            f' AND {self.table_alias}.id = ANY(:collection_id)'
        )

    def _apply_researcher_id_filter(self, value):
        self.params['researcher_id'] = str(value)
        self.filters_sql.append(
            f' AND {self.table_alias}.{self.researcher_id_col} = :researcher_id'
        )

    def _apply_lattes_id_filter(self, value):
        self.params['lattes_id'] = value
        self.filters_sql.append(' AND r.lattes_id = :lattes_id')

    def _apply_institution_id_filter(self, value):
        self.joins['institution'] = (
            'INNER JOIN institution i ON i.id = r.institution_id'
        )
        self.params['institution_id'] = value
        self.filters_sql.append(' AND i.id = :institution_id')

    def _apply_institution_filter(self, value):
        self.joins['institution'] = (
            'INNER JOIN institution i ON i.id = r.institution_id'
        )
        self.params['institution'] = value.split(';')
        self.filters_sql.append(' AND i.name = ANY(:institution)')

    def _apply_dep_id_filter(self, value):
        pass

    def _apply_departament_filter(self, value):
        pass

    def _apply_group_id_filter(self, value):
        self.joins['group'] = """
            INNER JOIN research_group_researcher rgr ON rgr.researcher_id = r.id
            INNER JOIN research_group rg ON rg.id = rgr.research_group_id
        """
        self.params['group_id'] = value
        self.filters_sql.append(' AND rgr.research_group_id = :group_id')

    def _apply_group_filter(self, value):
        self.joins['group'] = """
            INNER JOIN research_group_researcher rgr ON rgr.researcher_id = r.id
            INNER JOIN research_group rg ON rg.id = rgr.research_group_id
        """
        self.params['group'] = value.split(';')
        self.filters_sql.append(' AND rg.name = ANY(:group)')

    def _apply_graduate_program_id_filter(self, value):
        self.distinct_sql = 'DISTINCT'
        self.joins['program'] = f"""
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = {self.table_alias}.{self.researcher_id_col}
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        self.params['graduate_program_id'] = str(value)
        self.filters_sql.append(
            ' AND gpr.graduate_program_id = :graduate_program_id'
        )

    def _apply_graduate_program_filter(self, value):
        self.distinct_sql = 'DISTINCT'
        self.joins['program'] = f"""
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = {self.table_alias}.{self.researcher_id_col}
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        self.params['graduate_program'] = value.split(';')
        self.filters_sql.append(' AND gp.name = ANY(:graduate_program)')

    def _apply_city_filter(self, value):
        self.joins['researcher_production'] = (
            f'LEFT JOIN researcher_production rp ON rp.researcher_id = {self.table_alias}.{self.researcher_id_col}'
        )
        self.params['city'] = value.split(';')
        self.filters_sql.append(' AND rp.city = ANY(:city)')

    def _apply_area_filter(self, value):
        self.joins['researcher_production'] = (
            f'LEFT JOIN researcher_production rp ON rp.researcher_id = {self.table_alias}.{self.researcher_id_col}'
        )
        self.params['area'] = value.replace(' ', '_').split(';')
        self.filters_sql.append(' AND rp.great_area_ && :area')

    def _apply_modality_filter(self, value):
        self.distinct_sql = 'DISTINCT'
        self.joins['foment'] = (
            f'INNER JOIN foment f ON f.researcher_id = {self.table_alias}.{self.researcher_id_col}'
        )
        self.params['modality'] = value.split(';')
        self.filters_sql.append(' AND f.modality_name = ANY(:modality)')

    def _apply_graduation_filter(self, value):
        self.params['graduation'] = value.split(';')
        self.filters_sql.append(' AND r.graduation = ANY(:graduation)')

    def _get_base_sql_components(self):
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                f'{self.table_alias}.{self.distinct_col}', self.term_value
            )
            self.params.update(term_params)
            self.filters_sql.append(self._format_websearch(filter_terms))

        if self.year_value:
            self.params['year'] = self.year_value
            self.filters_sql.append(
                f' AND {self.table_alias}.{self.year_col}::INT >= :year'
            )

        if self.distinct_value in {'1', 1}:
            cols = [
                (
                    f'{self.table_alias}.{col.strip()}'
                    if '.' not in col
                    else col.strip()
                )
                for col in self.distinct_col.split(',')
            ]
            self.distinct_sql = f'DISTINCT ON ({", ".join(cols)})'

        return {
            'distinct': self.distinct_sql,
            'filters': ' '.join(self.filters_sql),
            'joins': ' '.join(self.joins.values()),
            'pagination': self.pagination_sql,
        }


class EventArticleQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(
            session, table_alias='bp', year_col='year_', distinct_col='title'
        )

    def build_sql(self) -> str:
        self.filters_sql.append(" AND bp.type = 'WORK_IN_EVENT'")
        components = self._get_base_sql_components()
        order_by = (
            'bp.title, bp.year_ DESC'
            if components['distinct']
            else 'bp.year_ DESC'
        )

        return f"""
            SELECT {components['distinct']}
              bp.id, bp.title, bp.title_en, bp.nature, bp.language,
              bp.means_divulgation, bp.homepage, bp.relevance,
              bp.scientific_divulgation, bp.authors, bp.year_,
              r.name, r.id AS researcher_id, r.lattes_id, r.lattes_10_id,
              bpew.event_classification, bpew.event_name,
              bpew.event_city, bpew.event_year,
              bpew.proceedings_title, bpew.volume, bpew.issue, bpew.series,
              bpew.start_page, bpew.end_page, bpew.publisher_name, bpew.publisher_city,
              bpew.event_name_english, bpew.identifier_number, bpew.isbn, bpew.stars
            FROM public.bibliographic_production bp
              INNER JOIN public.bibliographic_production_work_in_event bpew ON bpew.bibliographic_production_id = bp.id
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class ResearchProjectQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(
            session,
            table_alias='rp',
            year_col='start_year',
            distinct_col='project_name',
        )

    def _apply_year_filter(self, value):
        self.year_value = int(value)

    def _apply_type_filter(self, value):
        self.params['type'] = value.split(';')
        self.filters_sql.append(' AND rp.nature = ANY(:type)')

    def build_sql(self) -> str:
        if self.year_value:
            self.params['year'] = self.year_value
            self.filters_sql.append(' AND rp.start_year >= :year')

        components = self._get_base_sql_components()
        # Override components['filters'] if year handled manually but here we can just use the base logic if we set year_col correctly
        # But ResearchProject uses 'start_year' without ::INT cast usually.

        order_by = (
            'rp.project_name, rp.start_year DESC'
            if components['distinct']
            else 'rp.start_year DESC'
        )

        return f"""
            SELECT {components['distinct']}
              rp.id, rp.researcher_id, r.name, rp.start_year, rp.end_year,
              rp.agency_code, rp.agency_name, rp.project_name, rp.status,
              rp.nature, rp.number_undergraduates, rp.number_specialists,
              rp.number_academic_masters, rp.number_phd, rp.description,
              rpp.production, rpf.foment, rpc.components, rp.stars
            FROM public.research_project rp
              LEFT JOIN (SELECT project_id, JSONB_AGG(JSONB_BUILD_OBJECT('title', title, 'type', type)) AS production
                FROM public.research_project_production GROUP BY project_id) rpp ON rpp.project_id = rp.id
              LEFT JOIN (SELECT project_id, JSONB_AGG(JSONB_BUILD_OBJECT('agency_name', agency_name, 'agency_code', agency_code, 'nature', nature)) AS foment
                FROM public.research_project_foment GROUP BY project_id) rpf ON rpf.project_id = rp.id
              LEFT JOIN (SELECT project_id, JSONB_AGG(JSONB_BUILD_OBJECT('name', name, 'lattes_id', lattes_id, 'citations', citations)) AS components
                FROM public.research_project_components GROUP BY project_id) rpc ON rpc.project_id = rp.id
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class GuidanceQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(session, table_alias='g', distinct_col='title')

    def _apply_type_filter(self, value):
        self.params['type'] = value.split(';')
        self.filters_sql.append(' AND g.type = ANY(:type)')

    def build_sql(self) -> str:
        components = self._get_base_sql_components()
        order_by = (
            'g.title, g.year DESC' if components['distinct'] else 'g.year DESC'
        )

        return f"""
            SELECT {components['distinct']}
              g.id, g.title, g.nature, g.oriented, g.type, g.status,
              g.year, r.name, r.id AS researcher_id, r.lattes_id, g.stars
            FROM public.guidance g
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class ReportQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(session, table_alias='rr', distinct_col='title')

    def build_sql(self) -> str:
        components = self._get_base_sql_components()
        order_by = (
            'rr.title, rr.year DESC'
            if components['distinct']
            else 'rr.year DESC'
        )

        return f"""
            SELECT {components['distinct']}
              rr.id, r.name, rr.title, rr.year, rr.project_name,
              rr.financing_institutionc AS financing, rr.stars
            FROM public.research_report rr
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class SoftwareQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(session, table_alias='s', distinct_col='title')

    def build_sql(self) -> str:
        components = self._get_base_sql_components()
        order_by = (
            's.title, s.year DESC' if components['distinct'] else 's.year DESC'
        )

        return f"""
            SELECT {components['distinct']}
              s.id, s.title, s.year AS year, s.has_image, s.relevance,
              s.platform, s.goal, s.environment, s.availability, s.financing_institutionc,
              r.name, r.id AS researcher_id, r.lattes_id, s.stars
            FROM public.software s
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class BrandQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(session, table_alias='b', distinct_col='title')

    def build_sql(self) -> str:
        components = self._get_base_sql_components()
        order_by = (
            'b.title, b.year DESC' if components['distinct'] else 'b.year DESC'
        )

        return f"""
            SELECT {components['distinct']}
              b.id, b.title, b.year, b.has_image, b.relevance,
              b.goal, b.nature, b.stars,
              r.id AS researcher_id, r.lattes_id, r.name
            FROM public.brand b
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class ParticipationEventQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(session, table_alias='p', distinct_col='title')

    def _apply_type_filter(self, value):
        # Maps 'type' from DefaultFilters to 'nature' in participation_events
        self.params['nature_pe'] = value.split(';')
        self.filters_sql.append(' AND p.nature = ANY(:nature_pe)')

    def build_sql(self) -> str:
        components = self._get_base_sql_components()
        # Participation event always orders by title, year DESC in the prompt
        order_by = 'p.title, p.year DESC'

        return f"""
            SELECT {components['distinct']}
              r.name, p.id, p.title, p.event_name, p.nature,
              p.form_participation, p.year
            FROM public.participation_events p
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class ProfessionalExperienceQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(
            session,
            table_alias='rpe',
            researcher_id_col='researcher_id',
            distinct_col='researcher_id, enterprise',
        )

    def _apply_year_filter(self, value):
        self.params['year'] = int(value)
        self.filters_sql.append(
            ' AND COALESCE(rpe.end_year, rpe.start_year) >= :year'
        )

    def build_sql(self) -> str:
        components = self._get_base_sql_components()
        order_by = (
            'rpe.researcher_id, rpe.enterprise, rpe.start_year DESC'
            if components['distinct']
            else 'rpe.start_year DESC'
        )

        return f"""
            SELECT {components['distinct']}
              rpe.id, rpe.researcher_id, rpe.enterprise, rpe.start_year, rpe.end_year,
              rpe.employment_type, rpe.other_employment_type, rpe.functional_classification,
              rpe.other_functional_classification, rpe.workload_hours_weekly,
              rpe.exclusive_dedication, rpe.additional_info,
              r.lattes_id, r.name as researcher_name, r.graduation
            FROM public.researcher_professional_experience rpe
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class PatentQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(
            session,
            table_alias='p',
            year_col='development_year',
            distinct_col='title',
        )

    def build_sql(self) -> str:
        components = self._get_base_sql_components()
        order_by = (
            'p.title DESC, p.development_year DESC'
            if components['distinct']
            else 'p.development_year DESC'
        )

        return f"""
            SELECT {components['distinct']}
              p.id, p.title, p.category, p.relevance, p.has_image,
              p.development_year AS year, p.details, p.grant_date, p.deposit_date,
              r.id AS researcher, r.lattes_id, r.name AS name, p.code, p.stars
            FROM public.patent p
              {components['joins']}
            WHERE 1 = 1
              {components['filters']}
            ORDER BY {order_by}
            {components['pagination']};
        """


class ScholarshipQuery(BaseProductionQuery):
    def __init__(self, session):
        # Using researcher_id and call_title as distinct_col to allow unique scholarship listing per researcher/call
        super().__init__(
            session,
            table_alias='s',
            year_col=None,
            distinct_col='researcher_id, call_title',
        )

    def build_sql(self) -> str:
        components = self._get_base_sql_components()
        # Ensure researcher_id is not null as per old query
        filters = components['filters'] + ' AND s.researcher_id IS NOT NULL'

        order_by = (
            's.researcher_id, s.call_title, r.name ASC'
            if components['distinct']
            else 'r.name ASC'
        )

        return f"""
            SELECT {components['distinct']}
                s.researcher_id, r.name, s.modality_code, s.modality_name,
                s.call_title, s.category_level_code, s.funding_program_name,
                s.institute_name, s.aid_quantity, s.scholarship_quantity
            FROM foment s
                {components['joins']}
            WHERE 1 = 1
                {filters}
            ORDER BY {order_by}
            {components['pagination']};
        """


class MagazineSearchQuery(BaseQuery):
    SUPPORTED_FILTERS = {'initials', 'issn'}

    def __init__(self, session):
        super().__init__(session)
        self.initials_value = None
        self.issn_value = None

    def _apply_initials_filter(self, value):
        self.initials_value = value

    def _apply_issn_filter(self, value):
        self.issn_value = value

    def build_sql(self) -> str:
        filters = []
        if self.initials_value:
            self.params['initials'] = self.initials_value.lower() + '%'
            filters.append('AND LOWER(m.name) LIKE :initials')
        if self.issn_value:
            self.params['issn'] = self.issn_value.replace('-', '')
            filters.append("AND translate(m.issn, '-', '') = :issn")

        return f"""
            SELECT 
                m.id AS id, 
                m.name AS magazine, 
                issn, 
                jcr, 
                jcr_link, 
                qualis
            FROM 
                periodical_magazine m
            WHERE 1 = 1
                {' '.join(filters)}
            ORDER BY jcr ASC
            {self.pagination_sql};
        """


class RecentlyUpdatedQuery(BaseProductionQuery):
    def __init__(self, session):
        super().__init__(
            session, table_alias='b', year_col='year', distinct_col='title'
        )

    def build_sql(self) -> str:
        components = self._get_base_sql_components()

        return f"""
            SELECT DISTINCT ON (b.title)
                b.title,
                op.article_institution,
                array_cat(string_to_array(op.issn, ','), string_to_array(bpa.issn, ',')) AS issn,
                op.authors_institution,
                op.abstract,
                op.authors,
                op.language,
                COALESCE(op.citations_count, 0) AS citations_count,
                op.pdf,
                op.landing_page_url,
                op.keywords,
                r.id AS researcher_id,
                b.year,
                b.doi,
                bpa.qualis,
                bpa.periodical_magazine_name AS name_periodical,
                r.name AS researcher,
                r.lattes_id,
                bpa.jcr AS jif,
                bpa.jcr_link
            FROM bibliographic_production b
            LEFT JOIN bibliographic_production_article bpa ON bpa.bibliographic_production_id = b.id
            LEFT JOIN openalex_article op ON op.article_id = b.id
            {components['joins']}
            WHERE b.type = 'ARTICLE'
                {components['filters']}
            ORDER BY b.title, b.year DESC
            LIMIT 100;
        """
