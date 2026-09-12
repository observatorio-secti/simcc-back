from datetime import datetime
from typing import Optional

from sqlalchemy import text

from simcc.queries.base import BaseQuery
from simcc.repositories import tools


class BaseMetricsQuery(BaseQuery):
    SUPPORTED_FILTERS = {
        'researcher_id',
        'dep_id',
        'departament',
        'institution',
        'institution_id',
        'graduate_program_id',
        'graduate_program',
        'city',
        'area',
        'modality',
        'graduation',
        'type',
        'term',
        'terms',
        'year',
        'distinct',
    }

    def __init__(self, session):
        super().__init__(session)
        self.type_specific_filters = []
        self.join_type_specific = ''
        self.term_value = None
        self.year_value = None
        self.type_value = None
        self.distinct_value = None

    def _apply_researcher_id_filter(self, value):
        self.params['researcher_id'] = str(value)
        self.filters_sql.append(' AND r.id = :researcher_id')

    def _apply_institution_id_filter(self, value):
        self.params['institution_id'] = value
        self.filters_sql.append(' AND r.institution_id = :institution_id')

    def _apply_dep_id_filter(self, value):
        pass

    def _apply_departament_filter(self, value):
        pass

    def _apply_institution_filter(self, value):
        self.joins['institution'] = (
            'INNER JOIN institution i ON r.institution_id = i.id'
        )
        self.params['institution'] = value.split(';')
        self.filters_sql.append(' AND i.name = ANY(:institution)')

    def _apply_graduate_program_id_filter(self, value):
        self.joins['program'] = """
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = r.id
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        self.params['graduate_program_id'] = str(value)
        self.filters_sql.append(
            " AND gpr.graduate_program_id = :graduate_program_id AND gpr.type_ = 'PERMANENTE'"
        )

    def _apply_graduate_program_filter(self, value):
        self.joins['program'] = """
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = r.id
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        self.params['graduate_program'] = value.split(';')
        self.filters_sql.append(
            " AND gp.name = ANY(:graduate_program) AND gpr.type_ = 'PERMANENTE'"
        )

    def _apply_city_filter(self, value):
        self.joins['researcher_production'] = (
            'INNER JOIN researcher_production rp ON rp.researcher_id = r.id'
        )
        self.params['city'] = value.split(';')
        self.filters_sql.append(' AND rp.city = ANY(:city)')

    def _apply_area_filter(self, value):
        self.joins['researcher_production'] = (
            'INNER JOIN researcher_production rp ON rp.researcher_id = r.id'
        )
        self.params['area'] = value.replace(' ', '_').split(';')
        self.filters_sql.append(' AND rp.great_area_ && :area')

    def _apply_modality_filter(self, value):
        self.joins['foment'] = 'INNER JOIN foment f ON f.researcher_id = r.id'
        self.params['modality'] = value.split(';')
        if value != '*':
            self.filters_sql.append(' AND f.modality_name = ANY(:modality)')

    def _apply_graduation_filter(self, value):
        self.params['graduation'] = value.split(';')
        self.filters_sql.append(' AND r.graduation = ANY(:graduation)')

    def _apply_term_filter(self, value):
        self.term_value = value

    def _apply_terms_filter(self, value):
        self._apply_term_filter(value)

    def _apply_year_filter(self, value):
        self.year_value = value

    def _apply_type_filter(self, value):
        self.type_value = value

    def _apply_distinct_filter(self, value):
        self.distinct_value = value

    def _handle_type_filter(self):
        if not self.type_value:
            return

        type_value = self.type_value
        if type_value == 'ABSTRACT' and self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'r.abstract', self.term_value
            )
            self.params.update(term_params)
            self.type_specific_filters.append(
                self._format_websearch(filter_terms)
            )
        elif type_value in {
            'BOOK',
            'BOOK_CHAPTER',
            'ARTICLE',
            'WORK_IN_EVENT',
            'TEXT_IN_NEWSPAPER_MAGAZINE',
        }:
            self.join_type_specific = f"INNER JOIN bibliographic_production bp ON bp.researcher_id = r.id AND bp.type = '{type_value}'"
            if self.term_value:
                filter_terms, term_params = tools.websearch_filter(
                    'bp.title', self.term_value
                )
                self.params.update(term_params)
                self.type_specific_filters.append(
                    self._format_websearch(filter_terms)
                )
            if self.year_value:
                self.params['year_ts'] = int(self.year_value)
                self.type_specific_filters.append(' AND bp.year_ >= :year_ts')
        elif type_value == 'PATENT':
            self.join_type_specific = (
                'INNER JOIN patent p ON p.researcher_id = r.id'
            )
            if self.term_value:
                filter_terms, term_params = tools.websearch_filter(
                    'p.title', self.term_value
                )
                self.params.update(term_params)
                self.type_specific_filters.append(
                    self._format_websearch(filter_terms)
                )
            if self.year_value:
                self.params['year_ts'] = int(self.year_value)
                self.type_specific_filters.append(
                    ' AND p.development_year::INT >= :year_ts'
                )
        elif type_value == 'AREA':
            if not self.joins.get('researcher_production'):
                self.joins['researcher_production'] = (
                    'INNER JOIN researcher_production rp ON rp.researcher_id = r.id'
                )
            if self.term_value:
                filter_terms, term_params = tools.websearch_filter(
                    'rp.great_area', self.term_value
                )
                self.params.update(term_params)
                self.type_specific_filters.append(
                    self._format_websearch(filter_terms)
                )
        elif type_value == 'EVENT':
            self.join_type_specific = (
                'INNER JOIN event_organization e ON e.researcher_id = r.id'
            )
            if self.term_value:
                filter_terms, term_params = tools.websearch_filter(
                    'e.title', self.term_value
                )
                self.params.update(term_params)
                self.type_specific_filters.append(
                    self._format_websearch(filter_terms)
                )
            if self.year_value:
                self.params['year_ts'] = int(self.year_value)
                self.type_specific_filters.append(' AND e.year >= :year_ts')
        elif type_value == 'NAME' and self.term_value:
            name_filter, name_params = tools.names_filter(
                'r.name', self.term_value
            )
            self.type_specific_filters.append(name_filter)
            self.params.update(name_params)


class GraduateProgramProductionQuery(BaseQuery):
    SUPPORTED_FILTERS = {'graduate_program_id', 'year', 'dep_id'}

    def __init__(self, session):
        super().__init__(session)
        self.graduate_program_id = None
        self.base_year = 0
        self.dep_id = None

    def _apply_graduate_program_id_filter(self, value):
        if value and value != '0':
            self.graduate_program_id = str(value)

    def _apply_year_filter(self, value):
        self.base_year = int(value)

    def _apply_dep_id_filter(self, value):
        self.dep_id = value

    def build_sql(self) -> str:
        production_types = [
            'ARTICLE',
            'BOOK',
            'BOOK_CHAPTER',
            'WORK_IN_EVENT',
        ]

        self.params['year'] = self.base_year

        if self.graduate_program_id:
            self.params['graduate_program_id'] = self.graduate_program_id
            filter_program = (
                'AND gpr.graduate_program_id = :graduate_program_id'
            )

            bibliographic_queries = [
                f"""
                SELECT COUNT(gpr.graduate_program_id) AS qtd, '{prod}' AS type
                FROM public.bibliographic_production b
                JOIN graduate_program_researcher gpr ON b.researcher_id = gpr.researcher_id
                WHERE b.type = '{prod}' {filter_program} AND b.year_ >= :year
                GROUP BY type
                """
                for prod in production_types
            ]

            SCRIPT_SQL = f"""
                SELECT COUNT(gpr.graduate_program_id) AS qtd, 'PATENT' AS type
                FROM patent p
                JOIN graduate_program_researcher gpr ON gpr.researcher_id = p.researcher_id
                JOIN researcher r ON r.id = gpr.researcher_id
                WHERE p.development_year::int >= :year {filter_program} AND r.status = TRUE
                GROUP BY type

                UNION
                SELECT COUNT(gpr.graduate_program_id) AS qtd, 'SOFTWARE' AS type
                FROM software s
                JOIN graduate_program_researcher gpr ON gpr.researcher_id = s.researcher_id
                WHERE s.year >= :year {filter_program}
                GROUP BY type

                UNION
                SELECT COUNT(gpr.graduate_program_id) AS qtd, 'BRAND' AS type
                FROM brand b
                JOIN graduate_program_researcher gpr ON gpr.researcher_id = b.researcher_id
                WHERE b.year >= :year {filter_program}
                GROUP BY type

                UNION {' UNION '.join(bibliographic_queries)}

                UNION
                SELECT COUNT(*) AS qtd, r.graduation AS type
                FROM researcher r
                RIGHT JOIN graduate_program_researcher gpr ON gpr.researcher_id = r.id
                WHERE 1=1 {filter_program}
                GROUP BY r.graduation
            """

            researcher_sql = """
                SELECT COUNT(*) AS qtd FROM graduate_program_researcher 
                WHERE graduate_program_id = :graduate_program_id
            """
        else:
            dep_filter = ''
            researcher_filter = ''
            if self.dep_id:
                pass

            bibliographic_queries = [
                f"""
                SELECT COUNT(DISTINCT b.title) AS qtd, '{prod}' AS type
                FROM public.bibliographic_production b
                WHERE b.type = '{prod}' AND b.year_ >= :year {dep_filter}
                GROUP BY type
                """
                for prod in production_types
            ]

            SCRIPT_SQL = f"""
                SELECT COUNT(DISTINCT p.title) AS qtd, 'PATENT' AS type
                FROM patent p
                WHERE p.development_year::int >= :year {dep_filter}
                GROUP BY type

                UNION
                SELECT COUNT(DISTINCT s.title) AS qtd, 'SOFTWARE' AS type
                FROM software s
                WHERE s.year >= :year {dep_filter}
                GROUP BY type

                UNION
                SELECT COUNT(DISTINCT b.title) AS qtd, 'BRAND' AS type
                FROM brand b
                WHERE b.year >= :year {dep_filter}
                GROUP BY type

                UNION {' UNION '.join(bibliographic_queries)}

                UNION
                SELECT COUNT(*) AS qtd, UPPER(r.graduation) AS type
                FROM researcher r
                WHERE r.status = TRUE 
                AND r.id NOT IN (SELECT researcher_id FROM graduate_program_student)
                {researcher_filter}
                GROUP BY graduation
            """
            researcher_sql = 'SELECT COUNT(*) AS qtd FROM researcher r'

        self._researcher_sql = researcher_sql
        return SCRIPT_SQL

    async def execute(self):
        query = self.build_sql()
        result = await self.session.execute(text(query), self.params)
        rows = result.mappings().all()

        prod_map = {
            'BOOK': 'book',
            'WORK_IN_EVENT': 'work_in_event',
            'ARTICLE': 'article',
            'BOOK_CHAPTER': 'book_chapter',
            'PATENT': 'patent',
            'SOFTWARE': 'software',
            'BRAND': 'brand',
            'DOUTORADO': 'doctors',
            'MESTRADO': 'masters',
            'GRADUAÇÃO': 'graduate',
            'ESPECIALIZAÇÃO': 'specialization',
            'PÓS-DOUTORADO': 'pos_doctors',
        }

        data = {
            'id': self.graduate_program_id,
            'article': 0,
            'book': 0,
            'book_chapter': 0,
            'work_in_event': 0,
            'patent': 0,
            'software': 0,
            'brand': 0,
            'doctors': 0,
            'masters': 0,
            'graduate': 0,
            'specialization': 0,
            'pos_doctors': 0,
            'researcher': 0,
        }

        for row in rows:
            attr = prod_map.get(row['type'])
            if attr:
                data[attr] = row['qtd']

        res_count = await self.session.execute(
            text(self._researcher_sql), self.params
        )
        data['researcher'] = res_count.scalar() or 0

        return [data]


class GeneralProductionMetricsQuery(BaseQuery):
    SUPPORTED_FILTERS = {
        'year',
        'graduate_program_id',
        'dep_id',
        'researcher_id',
    }

    def __init__(self, session):
        super().__init__(session)
        self.year = datetime.now().year - 10  # Default to last 10 years
        self.graduate_program_id = None
        self.dep_id = None
        self.researcher_id = None

    def _apply_year_filter(self, value):
        self.year = int(value)

    def _apply_graduate_program_id_filter(self, value):
        self.graduate_program_id = str(value)

    def _apply_dep_id_filter(self, value):
        self.dep_id = value

    def _apply_researcher_id_filter(self, value):
        self.researcher_id = str(value)

    def build_sql(self) -> str:
        filters = ''
        if self.researcher_id:
            self.params['researcher_id'] = self.researcher_id
            filters += ' AND researcher_id = :researcher_id'
        if self.graduate_program_id:
            self.params['graduate_program_id'] = self.graduate_program_id
            filters += """
                AND researcher_id IN (
                    SELECT researcher_id FROM graduate_program_researcher 
                    WHERE graduate_program_id = :graduate_program_id
                )
            """
        if self.dep_id:
            pass

        self.params['year'] = self.year

        queries = {
            'guidance': f"""
                SELECT g.year::int, COUNT(*) as count_guidance,
                  COUNT(CASE WHEN g.status = 'Concluída' THEN 1 ELSE NULL END) as count_guidance_complete,
                  COUNT(CASE WHEN g.status = 'Em andamento' THEN 1 ELSE NULL END) as count_guidance_in_progress
                FROM guidance g
                WHERE g.year::int >= :year {filters}
                GROUP BY g.year ORDER BY g.year
            """,
            'books': f"""
                SELECT bp.year_::int as year, COUNT(DISTINCT title) AS count_book
                FROM public.bibliographic_production bp
                WHERE type = 'BOOK' AND bp.year_::int >= :year {filters}
                GROUP BY bp.year_ ORDER BY bp.year_
            """,
            'chapters': f"""
                SELECT bp.year_::int as year, COUNT(DISTINCT title) AS count_book_chapter
                FROM public.bibliographic_production bp
                WHERE type = 'BOOK_CHAPTER' AND bp.year_::int >= :year {filters}
                GROUP BY bp.year_ ORDER BY bp.year_
            """,
            'patents': f"""
                SELECT p.development_year::int AS year,
                  COUNT(CASE WHEN p.grant_date IS NULL THEN 1 ELSE NULL END) count_not_granted_patent,
                  COUNT(CASE WHEN p.grant_date IS NOT NULL THEN 1 ELSE NULL END) as count_granted_patent,
                  COUNT(*) as count_total
                FROM patent p
                WHERE p.development_year::int >= :year {filters}
                GROUP BY p.development_year ORDER BY p.development_year
            """,
            'software': f"""
                SELECT sw.year::int as year, COUNT(DISTINCT title) AS count_software
                FROM public.software sw
                WHERE sw.year::int >= :year {filters}
                GROUP BY sw.year ORDER BY sw.year
            """,
            'report': f"""
                SELECT rr.year::int as year, COUNT(DISTINCT title) AS count_report
                FROM research_report rr
                WHERE rr.year::int >= :year {filters}
                GROUP BY rr.year ORDER BY rr.year
            """,
            'articles': f"""
                SELECT bpa.qualis, bp.year_::int AS year,
                  COUNT(DISTINCT title) AS count_article
                FROM public.bibliographic_production bp
                INNER JOIN bibliographic_production_article bpa ON bpa.bibliographic_production_id = bp.id
                WHERE type = 'ARTICLE' AND bp.year_::int >= :year {filters}
                GROUP BY bpa.qualis, bp.year_ ORDER BY bpa.qualis, bp.year_
            """,
            'brand': f"""
                SELECT br.year::int as year, COUNT(DISTINCT br.title) AS count_brand
                FROM brand br
                WHERE br.year::int >= :year {filters}
                GROUP BY br.year ORDER BY br.year
            """,
            'patent': f"""
                SELECT br.development_year::int as year, COUNT(DISTINCT br.title) AS count_patent
                FROM patent br
                WHERE br.development_year::int >= :year {filters}
                GROUP BY br.development_year ORDER BY br.development_year
            """,
        }
        self._queries = queries
        return ''

    async def execute(self):
        self.build_sql()

        current_year = datetime.now().year
        data_frame = {
            y: {'year': y} for y in range(self.year, current_year + 1)
        }

        results = []
        for key, sql in self._queries.items():
            res = await self.session.execute(text(sql), self.params)
            results.append((key, res.mappings().all()))

        for key, rows in results:
            if key == 'articles':
                for row in rows:
                    y = row['year']
                    if y in data_frame:
                        q = row['qualis'].upper()
                        data_frame[y][q] = row['count_article']
                        data_frame[y]['count_article'] = (
                            data_frame[y].get('count_article', 0)
                            + row['count_article']
                        )
            else:
                for row in rows:
                    y = row['year']
                    if y in data_frame:
                        data_frame[y].update(dict(row))

        return list(data_frame.values())


class AcademicDegreeMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        self._handle_type_filter()
        filters_sql = ' '.join(self.filters_sql)
        type_specific_filters = ' '.join(self.type_specific_filters)

        SCRIPT_SQL = f"""
            SELECT r.graduation, COUNT(DISTINCT r.id) AS among
            FROM researcher r
                {' '.join(self.joins.values())}
                {self.join_type_specific}
            WHERE r.graduation IS NOT NULL
                {filters_sql}
                {type_specific_filters}
            GROUP BY r.graduation;
        """
        return SCRIPT_SQL


class GreatAreaMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        self._handle_type_filter()
        filters_sql = ' '.join(self.filters_sql)
        type_specific_filters = ' '.join(self.type_specific_filters)

        # Remove 'researcher_production' from joins if it's there to avoid duplicate alias 'rp'
        # as it is already in the FROM clause of this specific query
        joins_dict = self.joins.copy()
        if 'researcher_production' in joins_dict:
            del joins_dict['researcher_production']

        SCRIPT_SQL = f"""
            WITH areas AS (
                SELECT DISTINCT ON (r.id, ga)
                    r.id AS researcher_id,
                    UNNEST(rp.great_area_) AS ga
                FROM researcher_production rp
                    INNER JOIN researcher r ON r.id = rp.researcher_id
                    {' '.join(joins_dict.values())}
                    {self.join_type_specific}
                WHERE 1 = 1
                    {filters_sql}
                    {type_specific_filters}
            )
            SELECT REPLACE(areas.ga, '_', ' ') AS great_area, COUNT(areas.researcher_id) AS count
            FROM areas
            WHERE areas.ga IS NOT NULL AND areas.ga <> ''
            GROUP BY great_area
            ORDER BY count DESC;
        """
        return SCRIPT_SQL


class YearlyProductionMetricsQuery(BaseMetricsQuery):
    def __init__(self, session, production_type: str):
        super().__init__(session)
        self.production_type = production_type
        self.table_alias = 'bp'
        self.year_col = 'year'
        if production_type == 'TEXT_IN_NEWSPAPER_MAGAZINE':
            self.year_col = 'year_'

    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        term_filter = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                f'{self.table_alias}.title', self.term_value
            )
            self.params.update(term_params)
            term_filter = self._format_websearch(filter_terms)

        if self.year_value:
            self.params['year_metrics'] = int(self.year_value)
            filters_sql += f' AND {self.table_alias}.{self.year_col}::INT >= :year_metrics'

        distinct = 'DISTINCT' if self.distinct_value == '1' else ''

        # Base join with researcher is always needed for these metrics
        base_join = f"LEFT JOIN bibliographic_production bp ON bp.researcher_id = r.id AND bp.type = '{self.production_type}'"

        # Special case for Article Metrics (more aggregates)
        if self.production_type == 'ARTICLE':
            return self._build_article_sql(distinct, term_filter, filters_sql)

        SCRIPT_SQL = f"""
            SELECT bp.{self.year_col} AS year, COUNT({distinct} bp.title) AS among
            FROM researcher r
                {base_join}
                {' '.join(self.joins.values())}
            WHERE bp.{self.year_col} IS NOT NULL
                {term_filter}
                {filters_sql}
            GROUP BY bp.{self.year_col}
            ORDER BY bp.{self.year_col} ASC;
        """
        return SCRIPT_SQL

    def _build_article_sql(self, distinct, term_filter, filters_sql):
        article_joins = """
            INNER JOIN bibliographic_production_article bpa 
                ON bpa.bibliographic_production_id = bp.id
            LEFT JOIN openalex_article opa 
                ON opa.article_id = bp.id
        """

        jcr_cte = """
            WITH jcr_classification AS (
                SELECT DISTINCT bpa.bibliographic_production_id,
                    CASE
                        WHEN bpa.jcr = 'N/A' THEN 'not_applicable'
                        WHEN NULLIF(TRIM(bpa.jcr), '') IS NULL THEN 'without_jcr'
                        WHEN CAST(bpa.jcr AS NUMERIC) < 0.65 THEN 'very_low'
                        WHEN CAST(bpa.jcr AS NUMERIC) < 2.0 THEN 'low'
                        WHEN CAST(bpa.jcr AS NUMERIC) < 4.0 THEN 'medium'
                        ELSE 'high'
                    END AS jcr_category
                FROM bibliographic_production_article bpa
            )
            """

        SCRIPT_SQL = f"""
            {jcr_cte}

            SELECT 
                bp.year,
                SUM(COALESCE(opa.citations_count, 0)) AS citations,

                JSONB_BUILD_OBJECT(
                    'A1', COUNT(*) FILTER (WHERE bpa.qualis = 'A1'),
                    'A2', COUNT(*) FILTER (WHERE bpa.qualis = 'A2'),
                    'A3', COUNT(*) FILTER (WHERE bpa.qualis = 'A3'),
                    'A4', COUNT(*) FILTER (WHERE bpa.qualis = 'A4'),
                    'B1', COUNT(*) FILTER (WHERE bpa.qualis = 'B1'),
                    'B2', COUNT(*) FILTER (WHERE bpa.qualis = 'B2'),
                    'B3', COUNT(*) FILTER (WHERE bpa.qualis = 'B3'),
                    'B4', COUNT(*) FILTER (WHERE bpa.qualis = 'B4'),
                    'C', COUNT(*) FILTER (WHERE bpa.qualis = 'C'),
                    'SQ', COUNT(*) FILTER (
                        WHERE bpa.qualis = 'SQ'
                        OR bpa.qualis IS NULL
                        OR bpa.qualis = ''
                    )
                ) AS qualis,

                JSONB_BUILD_OBJECT(
                    'not_applicable', COUNT(*) FILTER (WHERE jc.jcr_category = 'not_applicable'),
                    'very_low', COUNT(*) FILTER (WHERE jc.jcr_category = 'very_low'),
                    'low', COUNT(*) FILTER (WHERE jc.jcr_category = 'low'),
                    'medium', COUNT(*) FILTER (WHERE jc.jcr_category = 'medium'),
                    'high', COUNT(*) FILTER (WHERE jc.jcr_category = 'high'),
                    'without_jcr', COUNT(*) FILTER (WHERE jc.jcr_category = 'without_jcr')
                ) AS jcr,

                COUNT({distinct} bp.title) AS among,
                COUNT(DISTINCT bp.doi) AS count_doi

            FROM researcher r

            LEFT JOIN bibliographic_production bp 
                ON bp.researcher_id = r.id
                AND bp.type = 'ARTICLE'

            {article_joins}

            LEFT JOIN jcr_classification jc
                ON jc.bibliographic_production_id = bp.id

            {' '.join(self.joins.values())}

            WHERE bp.year IS NOT NULL
                {term_filter}
                {filters_sql}

            GROUP BY bp.year
            ORDER BY bp.year ASC;
        """
        return SCRIPT_SQL


class ResearcherMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        self._handle_type_filter()
        filters_sql = ' '.join(self.filters_sql)
        type_specific_filters = ' '.join(self.type_specific_filters)

        count_among = 'COUNT(DISTINCT r.id) AS among'
        if self.type_value in {
            'BOOK',
            'BOOK_CHAPTER',
            'ARTICLE',
            'WORK_IN_EVENT',
            'TEXT_IN_NEWSPAPER_MAGAZINE',
        }:
            count_among = 'COUNT(DISTINCT bp.title) AS among'
        elif self.type_value == 'PATENT':
            count_among = 'COUNT(DISTINCT p.title) AS among'
        elif self.type_value == 'EVENT':
            count_among = 'COUNT(DISTINCT e.title) AS among'

        SCRIPT_SQL = f"""
            SELECT
                COUNT(DISTINCT r.id) AS researcher_count,
                COUNT(DISTINCT r.orcid) AS orcid_count,
                COUNT(DISTINCT opr.scopus) AS scopus_count,
                {count_among}
            FROM researcher r
                LEFT JOIN openalex_researcher opr ON opr.researcher_id = r.id
                {' '.join(self.joins.values())}
                {self.join_type_specific}
            WHERE 1 = 1
                {filters_sql}
                {type_specific_filters};
        """
        return SCRIPT_SQL


class PatentMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        term_filter = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'p.title', self.term_value
            )
            self.params.update(term_params)
            term_filter = self._format_websearch(filter_terms)

        if self.year_value:
            self.params['year_p'] = int(self.year_value)
            filters_sql += ' AND p.development_year::INT >= :year_p'

        distinct = 'DISTINCT' if self.distinct_value == '1' else ''

        SCRIPT_SQL = f"""
            SELECT 
                p.development_year AS year,
                COUNT({distinct} p.title) FILTER (WHERE p.grant_date IS NULL) AS NOT_GRANTED,
                COUNT({distinct} p.title) FILTER (WHERE p.grant_date IS NOT NULL) AS GRANTED
            FROM patent p
                INNER JOIN researcher r ON r.id = p.researcher_id
                {' '.join(self.joins.values())}
            WHERE p.development_year IS NOT NULL
                {term_filter}
                {filters_sql}
            GROUP BY p.development_year
            ORDER BY p.development_year ASC;
        """
        return SCRIPT_SQL


class GuidanceMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        term_filter = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'g.title', self.term_value
            )
            self.params.update(term_params)
            term_filter = self._format_websearch(filter_terms)

        if self.year_value:
            self.params['year_g'] = int(self.year_value)
            filters_sql += ' AND g.year::INT >= :year_g'

        distinct = (
            'DISTINCT ON (g.oriented, g.nature, g.year)'
            if self.distinct_value == '1'
            else ''
        )

        SCRIPT_SQL = f"""
            WITH Orientacoes AS (
                SELECT {distinct}
                    g.year AS year,
                    unaccent(lower(g.nature)) AS nature,
                    unaccent(lower(g.status)) AS status,
                    g.oriented AS oriented
                FROM guidance g
                    INNER JOIN researcher r ON r.id = g.researcher_id
                    {' '.join(self.joins.values())}
                WHERE 1 = 1
                    {filters_sql}
                    {term_filter}
                ORDER BY g.oriented, g.nature, g.year
            )
            SELECT year,
                COUNT(oriented) FILTER (WHERE nature LIKE '%iniciacao cientifica%' AND status = 'concluida') AS ic_completed,
                COUNT(oriented) FILTER (WHERE nature LIKE '%iniciacao cientifica%' AND status = 'em andamento') AS ic_in_progress,
                COUNT(oriented) FILTER (WHERE nature LIKE '%dissertacao de mestrado%' AND status = 'concluida') AS m_completed,
                COUNT(oriented) FILTER (WHERE nature LIKE '%dissertacao de mestrado%' AND status = 'em andamento') AS m_in_progress,
                COUNT(oriented) FILTER (WHERE nature LIKE '%tese de doutorado%' AND status = 'concluida') AS d_completed,
                COUNT(oriented) FILTER (WHERE nature LIKE '%tese de doutorado%' AND status = 'em andamento') AS d_in_progress,
                COUNT(oriented) FILTER (WHERE nature LIKE '%trabalho de conclusao de curso%graduacao%' AND status = 'concluida') AS g_completed,
                COUNT(oriented) FILTER (WHERE nature LIKE '%trabalho de conclusao de curso%graduacao%' AND status = 'em andamento') AS g_in_progress,
                COUNT(oriented) FILTER (WHERE nature LIKE '%monografia de conclusao de curso%especializacao%' AND status = 'concluida') AS e_completed,
                COUNT(oriented) FILTER (WHERE nature LIKE '%monografia de conclusao de curso%especializacao%' AND status = 'em andamento') AS e_in_progress,
                COUNT(oriented) FILTER (WHERE nature LIKE '%supervisao de pos-doutorado%' AND status = 'concluida') AS sd_completed,
                COUNT(oriented) FILTER (WHERE nature LIKE '%supervisao de pos-doutorado%' AND status = 'em andamento') AS sd_in_progress
            FROM Orientacoes
            WHERE year IS NOT NULL
            GROUP BY year
            ORDER BY year ASC;
        """
        return SCRIPT_SQL


class SpeakerMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        term_filter = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'pe.title', self.term_value
            )
            self.params.update(term_params)
            term_filter = self._format_websearch(filter_terms)

        if self.year_value:
            self.params['year_pe'] = int(self.year_value)
            filters_sql += ' AND pe.year::INT >= :year_pe'

        current_year = datetime.now().year
        self.params['current_year'] = current_year
        filters_sql += ' AND pe.year::INT <= :current_year'

        distinct = (
            'DISTINCT ON (pe.title)' if self.distinct_value == '1' else ''
        )

        SCRIPT_SQL = f"""
            WITH FilteredEvents AS (
                SELECT {distinct} pe.title, pe.year, pe.nature
                FROM participation_events pe
                    INNER JOIN researcher r ON r.id = pe.researcher_id
                    {' '.join(self.joins.values())}
                WHERE 1 = 1
                    {filters_sql}
                    {term_filter}
                ORDER BY pe.title, pe.year
            )
            SELECT fe.year,
                SUM(CASE WHEN fe.nature = 'Congresso' THEN 1 ELSE 0 END) AS congress,
                SUM(CASE WHEN fe.nature = 'Encontro' THEN 1 ELSE 0 END) AS meeting,
                SUM(CASE WHEN fe.nature = 'Oficina' THEN 1 ELSE 0 END) AS workshop,
                SUM(CASE WHEN fe.nature = 'Outra' THEN 1 ELSE 0 END) AS other,
                SUM(CASE WHEN fe.nature = 'Seminário' THEN 1 ELSE 0 END) AS seminar,
                SUM(CASE WHEN fe.nature = 'Simpósio' THEN 1 ELSE 0 END) AS symposium
            FROM FilteredEvents fe
            GROUP BY fe.year
            ORDER BY fe.year ASC;
        """
        return SCRIPT_SQL


class EducationMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        if self.year_value:
            self.params['year_e'] = int(self.year_value)
            filters_sql += ' AND (e.education_start::INT >= :year_e OR e.education_end::INT >= :year_e)'

        SCRIPT_SQL = f"""
            WITH EducacaoFiltrada AS (
                SELECT e.education_start, e.education_end, e.degree
                FROM education e
                    INNER JOIN researcher r ON r.id = e.researcher_id
                    {' '.join(self.joins.values())}
                WHERE 1 = 1
                    {filters_sql}
            ),
            EducacaoUnificada AS (
                SELECT education_start AS year, degree, 'START' AS event_type FROM EducacaoFiltrada WHERE education_start IS NOT NULL
                UNION ALL
                SELECT education_end AS year, degree, 'END' AS event_type FROM EducacaoFiltrada WHERE education_end IS NOT NULL
            )
            SELECT year, COUNT(degree) AS among, REPLACE(degree || '-' || event_type, '-', '_') AS degree
            FROM EducacaoUnificada
            GROUP BY year, degree, event_type
            ORDER BY year, degree;
        """
        return SCRIPT_SQL


class SoftwareMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        term_filter = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                's.title', self.term_value
            )
            self.params.update(term_params)
            term_filter = self._format_websearch(filter_terms)

        if self.year_value:
            self.params['year_s'] = int(self.year_value)
            filters_sql += ' AND s.year::INT >= :year_s'

        distinct = (
            'DISTINCT ON (s.title)' if self.distinct_value == '1' else ''
        )

        SCRIPT_SQL = f"""
            WITH FilteredSoftware AS (
                SELECT {distinct} s.year, s.title
                FROM software s
                    INNER JOIN researcher r ON r.id = s.researcher_id
                    {' '.join(self.joins.values())}
                WHERE 1 = 1
                    {filters_sql}
                    {term_filter}
                ORDER BY s.title, s.year
            )
            SELECT fs.year, COUNT(fs.title) AS among
            FROM FilteredSoftware fs
            GROUP BY fs.year
            ORDER BY fs.year ASC;
        """
        return SCRIPT_SQL


class ResearchReportMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        term_filter = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'rr.title', self.term_value
            )
            self.params.update(term_params)
            term_filter = self._format_websearch(filter_terms)

        if self.year_value:
            self.params['year_rr'] = int(self.year_value)
            filters_sql += ' AND rr.year::INT >= :year_rr'

        distinct = (
            'DISTINCT ON (rr.title)' if self.distinct_value == '1' else ''
        )

        SCRIPT_SQL = f"""
            WITH FilteredResearchReport AS (
                SELECT {distinct} rr.year, rr.title
                FROM research_report rr
                    INNER JOIN researcher r ON r.id = rr.researcher_id
                    {' '.join(self.joins.values())}
                WHERE 1 = 1
                    {filters_sql}
                    {term_filter}
                ORDER BY rr.title, rr.year
            )
            SELECT frr.year, COUNT(frr.title) AS among
            FROM FilteredResearchReport frr
            GROUP BY frr.year
            ORDER BY frr.year ASC;
        """
        return SCRIPT_SQL


class BrandMetricsQuery(BaseMetricsQuery):
    def __init__(self, session, nature: Optional[str] = None):
        super().__init__(session)
        self.nature = nature

    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        if self.nature:
            self.params['nature_b'] = self.nature.split(';')
            filters_sql += ' AND b.nature = ANY(:nature_b)'

        term_filter = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'b.title', self.term_value
            )
            self.params.update(term_params)
            term_filter = self._format_websearch(filter_terms)

        if self.year_value:
            self.params['year_b'] = int(self.year_value)
            filters_sql += ' AND b.year::INT >= :year_b'

        distinct = (
            'DISTINCT ON (b.title)' if self.distinct_value == '1' else ''
        )

        SCRIPT_SQL = f"""
            WITH FilteredBrands AS (
                SELECT {distinct} b.title, b.year
                FROM brand b
                    INNER JOIN researcher r ON r.id = b.researcher_id
                    {' '.join(self.joins.values())}
                WHERE 1 = 1
                    {filters_sql}
                    {term_filter}
                ORDER BY b.title, b.year
            )
            SELECT fb.year, COUNT(fb.title) AS among
            FROM FilteredBrands fb
            GROUP BY fb.year
            ORDER BY fb.year ASC;
        """
        return SCRIPT_SQL


class ResearchProjectMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)
        term_filter = ''
        if self.term_value:
            filter_terms, term_params = tools.websearch_filter(
                'rpj.project_name', self.term_value
            )
            self.params.update(term_params)
            term_filter = self._format_websearch(filter_terms)

        if self.year_value:
            self.params['year_rpj'] = int(self.year_value)
            filters_sql += ' AND rpj.start_year::INT >= :year_rpj'

        distinct = (
            'DISTINCT ON (rpj.project_name)'
            if self.distinct_value == '1'
            else ''
        )

        SCRIPT_SQL = f"""
            WITH rp_ AS (
                SELECT {distinct} nature, start_year AS year, project_name
                FROM research_project rpj
                    INNER JOIN researcher r ON r.id = rpj.researcher_id
                    {' '.join(self.joins.values())}
                WHERE start_year IS NOT NULL
                    AND {filters_sql.lstrip(' AND') or '1=1'}
                    {term_filter}
                ORDER BY project_name
            ),
            nature_counts AS (
                SELECT year, nature, COUNT(*) as count
                FROM rp_
                GROUP BY year, nature
            )
            SELECT 
                year, 
                JSONB_OBJECT_AGG(nature, count) AS nature, 
                SUM(count) AS among
            FROM nature_counts
            GROUP BY year
            ORDER BY year ASC;
        """

        return SCRIPT_SQL


class LattesUpdateMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        self._handle_type_filter()
        filters_sql = ' '.join(self.filters_sql)
        type_specific_filters = ' '.join(self.type_specific_filters)

        SCRIPT_SQL = f"""
            SELECT
                COUNT(DISTINCT r.id) AS total,
                COUNT(DISTINCT r.id) FILTER (WHERE r.last_update < CURRENT_DATE - INTERVAL '3 months') AS over_3_months,
                COUNT(DISTINCT r.id) FILTER (WHERE r.last_update < CURRENT_DATE - INTERVAL '6 months') AS over_6_months
            FROM
                public.researcher r
                {' '.join(self.joins.values())}
                {self.join_type_specific}
            WHERE 1=1
                AND r.status IS True
                {filters_sql}
                {type_specific_filters};
        """
        return SCRIPT_SQL


class ScholarshipMetricsQuery(BaseMetricsQuery):
    def build_sql(self) -> str:
        filters_sql = ' '.join(self.filters_sql)

        SCRIPT_SQL = f"""
            SELECT
                f.modality_code,
                f.category_level_code,
                COUNT(DISTINCT f.researcher_id) AS count
            FROM foment f
                INNER JOIN researcher r ON r.id = f.researcher_id
                {' '.join(self.joins.values())}
            WHERE 1 = 1
                {filters_sql}
            GROUP BY f.modality_code, f.category_level_code
            ORDER BY count DESC;
        """
        return SCRIPT_SQL


class MagazineMetricsQuery(BaseQuery):
    SUPPORTED_FILTERS = {'issn', 'initials'}

    def __init__(self, session):
        super().__init__(session)
        self.issn_value = None
        self.initials_value = None

    def _apply_issn_filter(self, value):
        self.issn_value = value

    def _apply_initials_filter(self, value):
        self.initials_value = value

    def build_sql(self) -> str:
        filters = []
        if self.initials_value:
            self.params['initials'] = self.initials_value.lower() + '%'
            filters.append('AND LOWER(name) LIKE :initials')
        if self.issn_value:
            self.params['issn'] = self.issn_value.replace('-', '')
            filters.append("AND translate(issn, '-', '') = :issn")

        return f"""
            SELECT COUNT(*) AS among
            FROM periodical_magazine m
            WHERE 1 = 1
                {' '.join(filters)}
        """
