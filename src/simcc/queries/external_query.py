from typing import Any, Optional

from simcc.queries.base import BaseQuery
from simcc.repositories import tools


class DocenteSearchQuery(BaseQuery):
    SUPPORTED_FILTERS = {
        'type',
        'term',
        'terms',
        'year',
        'dep_id',
        'departament',
        'graduate_program_id',
        'graduate_program',
        'researcher_id',
        'city',
        'area',
        'modality',
        'graduation',
        'distinct',
    }

    def __init__(self, session):
        super().__init__(session)
        self.type_filter = ''
        self.filter_name = ''
        self.year_filter = ''
        self.where_extra = ''
        self.distinct_flag = False

    def _apply_type_filter(self, value):
        pass  # Handled in build_sql or via term

    def _apply_term_filter(self, value):
        # This needs to know the type, so we'll handle it in build_sql
        pass

    def _apply_terms_filter(self, value):
        self._apply_term_filter(value)

    def _apply_year_filter(self, value):
        self.params['year'] = int(value)

    def _apply_dep_id_filter(self, value):
        pass

    def _apply_departament_filter(self, value):
        pass

    def _apply_graduate_program_id_filter(self, value):
        self.distinct_flag = True
        self.joins['program'] = """
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = ur.researcher_id
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        self.params['program_id'] = str(value)
        self.where_extra += " AND gpr.graduate_program_id = :program_id AND gpr.type_ = 'PERMANENTE'"

    def _apply_graduate_program_filter(self, value):
        self.distinct_flag = True
        self.joins['program'] = """
            INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = ur.researcher_id
            INNER JOIN graduate_program gp ON gpr.graduate_program_id = gp.graduate_program_id
        """
        self.params['graduate_program'] = value.split(';')
        self.where_extra += " AND gp.name = ANY(:graduate_program) AND gpr.type_ = 'PERMANENTE'"

    def _apply_researcher_id_filter(self, value):
        self.params['researcher_id'] = str(value)
        self.where_extra += ' AND ur.researcher_id = :researcher_id'

    def _apply_city_filter(self, value):
        self.joins['researcher_production'] = (
            'LEFT JOIN researcher_production rp_prod ON rp_prod.researcher_id = ur.researcher_id'
        )
        self.params['city'] = value.split(';')
        self.where_extra += ' AND rp_prod.city = ANY(:city)'

    def _apply_area_filter(self, value):
        self.joins['researcher_production'] = (
            'LEFT JOIN researcher_production rp_prod ON rp_prod.researcher_id = ur.researcher_id'
        )
        self.params['area'] = value.replace(' ', '_').split(';')
        self.where_extra += " AND STRING_TO_ARRAY(REPLACE(rp_prod.great_area, ' ', '_'), ';') && :area"

    def _apply_modality_filter(self, value):
        self.joins['foment'] = (
            'INNER JOIN foment f ON f.researcher_id = ur.researcher_id'
        )
        if value != '*':
            self.params['modality'] = value.split(';')
            self.where_extra += ' AND f.modality_name = ANY(:modality)'

    def _apply_graduation_filter(self, value):
        self.params['graduation'] = value.split(';')
        self.where_extra += ' AND ur.academic_degree = ANY(:graduation)'

    def _apply_distinct_filter(self, value):
        if value in ['true', True, '1', 1]:
            self.distinct_flag = True

    def build_sql(self) -> str:
        # Complex logic for type and term
        type_val = getattr(self, '_type_val', None)
        term_val = getattr(self, '_term_val', None)

        join_filter = ''
        type_filter = ''
        year_filter = ''
        filter_name = ''

        if type_val == 'ABSTRACT' and term_val:
            term_sql, term_params = tools.websearch_filter(
                'r.abstract', term_val
            )
            self.params.update(term_params)
            type_filter = self._format_websearch(term_sql)
        elif type_val in [
            'BOOK',
            'BOOK_CHAPTER',
            'ARTICLE',
            'WORK_IN_EVENT',
            'TEXT_IN_NEWSPAPER_MAGAZINE',
        ]:
            join_filter = f"INNER JOIN bibliographic_production bp ON bp.researcher_id = ur.researcher_id AND bp.type = '{type_val}'"
            if term_val:
                term_sql, term_params = tools.websearch_filter(
                    'bp.title', term_val
                )
                self.params.update(term_params)
                type_filter = self._format_websearch(term_sql)
            if 'year' in self.params:
                year_filter = 'AND bp.year_::int >= :year'
        elif type_val == 'PATENT':
            join_filter = (
                'INNER JOIN patent p ON p.researcher_id = ur.researcher_id'
            )
            if term_val:
                term_sql, term_params = tools.websearch_filter(
                    'p.title', term_val
                )
                self.params.update(term_params)
                type_filter = self._format_websearch(term_sql)
            if 'year' in self.params:
                year_filter = 'AND p.development_year::int >= :year'
        elif type_val == 'AREA' and term_val:
            join_filter = 'INNER JOIN researcher_production rp ON rp.researcher_id = ur.researcher_id'
            term_sql, term_params = tools.websearch_filter(
                'rp.great_area', term_val
            )
            self.params.update(term_params)
            type_filter = self._format_websearch(term_sql)
        elif type_val == 'EVENT':
            join_filter = 'INNER JOIN event_organization e ON e.researcher_id = ur.researcher_id'
            if term_val:
                term_sql, term_params = tools.websearch_filter(
                    'e.title', term_val
                )
                self.params.update(term_params)
                type_filter = self._format_websearch(term_sql)
            if 'year' in self.params:
                year_filter = 'AND e.year::int >= :year'
        elif type_val == 'NAME' and term_val:
            name_sql, term_params = tools.names_filter(
                'ur.full_name', term_val
            )
            self.params.update(term_params)
            filter_name = name_sql

        distinct_clause = 'DISTINCT' if self.distinct_flag else ''

        return f"""
            SELECT {distinct_clause} ur.researcher_id, ur.full_name, ur.gender, ur.status_code, ur.work_regime,
                ur.job_class, ur.job_title, ur.job_rank, ur.job_reference_code, ur.academic_degree,
                ur.organization_entry_date, ur.last_promotion_date,
                ur.employment_status_description, ur.department_name, ur.career_category,
                ur.academic_unit, ur.unit_code, ur.function_code, ur.position_code,
                ur.leadership_start_date, ur.leadership_end_date, ur.current_function_name,
                ur.function_location, ur.registration_number, ur.ufmg_registration_number,
                ur.semester_reference
            FROM ufmg.researcher ur
            {join_filter}
            {' '.join(self.joins.values())}
            WHERE 1 = 1
            {type_filter}
            {filter_name}
            {year_filter}
            {self.where_extra}
            ORDER BY ur.full_name;
        """

    def apply_filters(self, filters: Any):
        self._type_val = getattr(filters, 'type', None)
        self._term_val = getattr(filters, 'term', None)
        super().apply_filters(filters)


class DepartmentSearchQuery(BaseQuery):
    def __init__(self, session, dep_id: Optional[str] = None):
        super().__init__(session)
        self.dep_id = dep_id

    def build_sql(self) -> str:
        filters = ''
        if self.dep_id:
            self.params['dep_id'] = self.dep_id
            filters = 'AND d.dep_id = :dep_id'

        return f"""
            WITH researchers AS (
                SELECT dep_id, ARRAY_AGG(r.lattes_id) AS researchers
                FROM ufmg.departament_researcher dp
                LEFT JOIN researcher r ON dp.researcher_id = r.id
                GROUP BY dep_id
                HAVING COUNT(r.id) >= 1
            )
            SELECT d.dep_id, d.org_cod, d.dep_nom, d.dep_des, d.dep_email, d.dep_site,
                d.dep_sigla, d.dep_tel, COALESCE(r.researchers, ARRAY[]::text[]) AS researchers
            FROM ufmg.departament d
            LEFT JOIN researchers r ON r.dep_id = d.dep_id
            WHERE 1 = 1
            {filters}
        """


class ResearcherArticleProductionQuery(BaseQuery):
    def __init__(
        self,
        session,
        program_id: Optional[str] = None,
        dep_id: Optional[str] = None,
        year: int = 2020,
    ):
        super().__init__(session)
        self.program_id = program_id
        self.dep_id = dep_id
        self.year = year

    def build_sql(self) -> str:
        filters = ''
        join_program = ''
        join_departament = ''

        if self.dep_id:
            pass

        if self.program_id:
            self.params['program_id'] = str(self.program_id)
            filters += " AND gpr.graduate_program_id = :program_id AND gpr.type_ = 'PERMANENTE'"
            join_program = 'INNER JOIN graduate_program_researcher gpr ON gpr.researcher_id = r.id'

        self.params['year'] = self.year
        filters += ' AND bp.year_::int >= :year'

        return f"""
            SELECT r.name, bpa.qualis, COUNT(*) AS among, bp.year_ as year,
                COALESCE(SUM(opa.citations_count), 0) AS citations
            FROM researcher r
            LEFT JOIN bibliographic_production bp ON bp.researcher_id = r.id
            RIGHT JOIN bibliographic_production_article bpa ON bpa.bibliographic_production_id = bp.id
            LEFT JOIN openalex_article opa ON opa.article_id = bp.id
            {join_program}
            {join_departament}
            WHERE 1 = 1
            {filters}
            GROUP BY r.id, bpa.qualis, bp.year_;
        """


class ResearcherDataQuery(BaseQuery):
    def __init__(
        self, session, cpf: Optional[str] = None, name: Optional[str] = None
    ):
        super().__init__(session)
        self.cpf = cpf
        self.name = name

    def build_sql(self) -> str:
        filters = ''
        if self.cpf:
            cpf_clean = self.cpf.replace('.', '').replace('-', '')
            self.params['cpf'] = cpf_clean
            filters += " AND REPLACE(REPLACE(cpf, '.', ''), '-', '') = :cpf"
        if self.name:
            self.params['name'] = self.name + '%'
            filters += ' AND nome ILIKE :name'

        return f"""
            SELECT nome, cpf, classe, nivel, inicio, fim, tempo_nivel,
                tempo_acumulado, arquivo
            FROM ufmg.researcher_data
            WHERE 1 = 1
            {filters}
        """


class TechnicianQuery(BaseQuery):
    def build_sql(self) -> str:
        return """
            SELECT technician_id, full_name, gender, status_code, work_regime,
                job_class, job_title, job_rank, job_reference_code, academic_degree,
                organization_entry_date, last_promotion_date,
                employment_status_description, department_name, career_category,
                academic_unit, unit_code, function_code, position_code,
                leadership_start_date, leadership_end_date, current_function_name,
                function_location, registration_number, ufmg_registration_number,
                semester_reference
            FROM ufmg.technician
        """


class WordFrequencyQuery(BaseQuery):
    def __init__(self, session, term: str, stopwords: list[str]):
        super().__init__(session)
        self.term = term
        self.stopwords = stopwords

    def build_sql(self) -> str:
        self.params['term'] = self.term + '%'
        self.params['stopwords'] = self.stopwords

        return r"""
            WITH words AS (
                SELECT regexp_split_to_table(translate(b.title, '-\.:,;''', ' '), '\s+') AS word
                FROM bibliographic_production b
                WHERE type = 'ARTICLE'),
            words_count AS (
                SELECT COUNT(*) AS frequency, LOWER(word) AS word
                FROM words
                WHERE word ~ '\w+'
                GROUP BY LOWER(word))
            SELECT word, frequency AS freq
            FROM words_count
            WHERE CHAR_LENGTH(word) > 3
                AND TRIM(word) <> ALL(:stopwords)
                AND unaccent(word) ILIKE :term
            ORDER BY frequency DESC
            LIMIT 10;
        """
