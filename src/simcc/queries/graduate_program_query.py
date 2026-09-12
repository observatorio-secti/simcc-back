from typing import Set

from simcc.queries.base import BaseQuery
from simcc.repositories import tools


class GraduateProgramQuery(BaseQuery):
    SUPPORTED_FILTERS: Set[str] = {'graduate_program_id', 'institution'}

    def _apply_graduate_program_id_filter(self, value):
        self.params['graduate_program_id'] = value
        self.filters_sql.append(
            'AND gp.graduate_program_id = :graduate_program_id'
        )

    def _apply_institution_filter(self, value):
        self.joins['institution'] = (
            'LEFT JOIN institution i ON gp.institution_id = i.id'
        )
        self.params['institution'] = f'{value}%'
        self.filters_sql.append('AND i.name ILIKE :institution')

    def build_sql(self) -> str:
        # Garante que o join da instituição exista se não foi ativado pelo filtro,
        # pois precisamos de i.name no SELECT base
        if 'institution' not in self.joins:
            self.joins['institution'] = (
                'LEFT JOIN institution i ON i.id = gp.institution_id'
            )

        filters = ' '.join(self.filters_sql)
        joins = ' '.join(self.joins.values())

        return f"""
        WITH permanent AS (
            SELECT graduate_program_id, COUNT(DISTINCT researcher_id) AS qtd_permanente
            FROM graduate_program_researcher
            WHERE type_ = 'PERMANENTE'
            GROUP BY graduate_program_id
        ),
        collaborators AS (
            SELECT graduate_program_id, COUNT(DISTINCT researcher_id) AS qtd_colaborador
            FROM graduate_program_researcher
            WHERE type_ = 'COLABORADOR'
            GROUP BY graduate_program_id
        ),
        students AS (
            SELECT graduate_program_id, COUNT(DISTINCT researcher_id) AS qtd_estudantes
            FROM graduate_program_student
            GROUP BY graduate_program_id
        ),
        researchers AS (
            SELECT graduate_program_id, ARRAY_AGG(DISTINCT r.lattes_id) AS researchers
            FROM graduate_program_researcher gpr
                LEFT JOIN researcher r ON gpr.researcher_id = r.id
            GROUP BY graduate_program_id
            HAVING COUNT(r.id) >= 1
        )
        SELECT 
            gp.graduate_program_id, 
            gp.code, 
            gp.name, 
            gp.name_en, 
            gp.basic_area,
            gp.cooperation_project, 
            UPPER(gp.area) AS area, 
            UPPER(gp.modality) AS modality,
            INITCAP(gp.type) AS type, 
            gp.rating, 
            gp.institution_id, 
            gp.state, 
            UPPER(gp.city) AS city,
            gp.region, 
            gp.url_image, 
            gp.acronym, 
            gp.description, 
            gp.visible, 
            gp.site,
            gp.coordinator, 
            gp.email, 
            gp.start, 
            gp.phone, 
            gp.periodicity,
            COALESCE(p.qtd_permanente, 0) AS qtd_permanente, 
            COALESCE(c.qtd_colaborador, 0) AS qtd_colaborador, 
            COALESCE(s.qtd_estudantes, 0) AS qtd_estudantes, 
            i.name AS institution,
            COALESCE(r.researchers, ARRAY[]::text[]) AS researchers
        FROM public.graduate_program gp
            LEFT JOIN permanent p ON gp.graduate_program_id = p.graduate_program_id
            LEFT JOIN students s ON gp.graduate_program_id = s.graduate_program_id
            LEFT JOIN collaborators c ON gp.graduate_program_id = c.graduate_program_id
            LEFT JOIN researchers r ON r.graduate_program_id = gp.graduate_program_id
            {joins}
        WHERE 1 = 1
            {filters}
        """


class ResearchLinesQuery(BaseQuery):
    SUPPORTED_FILTERS: Set[str] = {
        'graduate_program_id',
        'institution',
        'term',
    }

    def _apply_graduate_program_id_filter(self, value):
        self.params['graduate_program_id'] = value
        self.filters_sql.append(
            'AND lgp.graduate_program_id = :graduate_program_id'
        )

    def _apply_institution_filter(self, value):
        self.joins['institution'] = (
            'LEFT JOIN institution i ON gp.institution_id = i.id'
        )
        self.params['institution'] = f'{value}%'
        self.filters_sql.append('AND i.name ILIKE :institution')

    def _apply_term_filter(self, value):
        sql_term, params = tools.websearch_filter('lgp.name', value)
        self.params.update(params)
        self.filters_sql.append(self._format_websearch(sql_term))

    def build_sql(self) -> str:
        filters = ' '.join(self.filters_sql)
        joins = ' '.join(self.joins.values())

        return f"""
        SELECT lgp.graduate_program_id, lgp.name, lgp.area, start_year, end_year
        FROM public.research_lines_programs lgp
            LEFT JOIN graduate_program gp
                ON gp.graduate_program_id = lgp.graduate_program_id
            {joins}
        WHERE 1 = 1
            {filters}
        """


class GraduateProgramResearcherQuery(BaseQuery):
    SUPPORTED_FILTERS: Set[str] = {'graduate_program_id'}

    def _apply_graduate_program_id_filter(self, value):
        self.params['graduate_program_id'] = value
        self.filters_sql.append(
            'AND gpr.graduate_program_id = :graduate_program_id'
        )

    def build_sql(self) -> str:
        filters = ' '.join(self.filters_sql)

        return f"""
        SELECT
            r.id AS researcher_id,
            r.name,
            graduate_program_id,
            gpr.type_ AS type,
            gpr.year
        FROM
            graduate_program_researcher gpr
            LEFT JOIN researcher r ON gpr.researcher_id = r.id
        WHERE 1 = 1
            {filters}
        """


class GraduateProgramArticleProductionQuery(BaseQuery):
    SUPPORTED_FILTERS: Set[str] = {
        'graduate_program_id',
        'dep_id',
        'year',
    }

    def __init__(self, session, program_id=None, dep_id=None, year=2020):
        super().__init__(session)
        self.program_id = program_id
        self.dep_id = dep_id
        self.year = year

    def _apply_graduate_program_id_filter(self, value):
        self.joins['program'] = """
            INNER JOIN graduate_program_researcher gpr
            ON gpr.researcher_id = r.id
            """
        self.params['program_id'] = value
        self.filters_sql.append(
            "AND gpr.graduate_program_id = :program_id AND gpr.type_ = 'PERMANENTE'"
        )

    def _apply_dep_id_filter(self, value):
        pass

    def _apply_year_filter(self, value):
        self.params['year'] = int(value)
        self.filters_sql.append('AND bp.year_ >= :year')

    def build_sql(self) -> str:
        if self.program_id:
            self._apply_graduate_program_id_filter(self.program_id)
        if self.dep_id:
            self._apply_dep_id_filter(self.dep_id)
        if self.year:
            self._apply_year_filter(self.year)

        filters = ' '.join(self.filters_sql)
        joins = ' '.join(self.joins.values())

        return f"""
        SELECT 
            r.name, 
            bp.year_ AS year,
            COUNT(*) FILTER (WHERE bpa.qualis = 'A1') AS a1,
            COUNT(*) FILTER (WHERE bpa.qualis = 'A2') AS a2,
            COUNT(*) FILTER (WHERE bpa.qualis = 'A3') AS a3,
            COUNT(*) FILTER (WHERE bpa.qualis = 'A4') AS a4,
            COUNT(*) FILTER (WHERE bpa.qualis = 'B1') AS b1,
            COUNT(*) FILTER (WHERE bpa.qualis = 'B2') AS b2,
            COUNT(*) FILTER (WHERE bpa.qualis = 'B3') AS b3,
            COUNT(*) FILTER (WHERE bpa.qualis = 'B4') AS b4,
            COUNT(*) FILTER (WHERE bpa.qualis = 'C') AS c,
            COUNT(*) FILTER (WHERE bpa.qualis = 'SQ' OR bpa.qualis IS NULL) AS sq,
            COALESCE(SUM(opa.citations_count), 0)::INT AS citations
        FROM researcher r
            LEFT JOIN bibliographic_production bp ON bp.researcher_id = r.id
            INNER JOIN bibliographic_production_article bpa
                ON bpa.bibliographic_production_id = bp.id
            LEFT JOIN openalex_article opa ON opa.article_id = bp.id
            {joins}
        WHERE 1 = 1
            {filters}
        GROUP BY r.id, r.name, bp.year_
        ORDER BY r.name, bp.year_ DESC;
        """
