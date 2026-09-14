from typing import override

from simcc.queries.base import BaseQuery


class FatAreaSpecialtyQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT asp.id::TEXT AS area_specialty_id, researcher_id::TEXT,
            asp.name::TEXT AS area_specialty
        FROM researcher_area_expertise r
        INNER JOIN area_specialty asp ON asp.id = r.area_specialty_id;
        """


class FatGreatAreaQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT gae.id::TEXT AS great_area_id, researcher_id::TEXT,
            REPLACE(gae.name, '_', ' ')::TEXT AS name
        FROM great_area_expertise gae
            LEFT JOIN researcher_area_expertise r
                ON gae.id = r.great_area_expertise_id;
        """


class DimAreaSpecialtyQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT, REPLACE(name, '_', ' ')::TEXT AS name FROM area_specialty;
        """


class DimGreatAreaQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT, REPLACE(name, '_', ' ')::TEXT AS name
        FROM great_area_expertise;
        """


class FatOpenalexResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT researcher_id::TEXT, h_index::TEXT, relevance_score::TEXT, works_count::TEXT,
            cited_by_count::TEXT, i10_index::TEXT, scopus::TEXT, orcid::TEXT, openalex::TEXT
        FROM openalex_researcher;
        """


class ResearcherAreaLeaderQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT r.lattes_id::TEXT, a.name::TEXT AS area_leader, ra.focal_point::TEXT
        FROM admin.researcher_area ra
        LEFT JOIN admin.areas a ON a.id = ra.area_id
        LEFT JOIN admin.researcher r ON r.researcher_id = ra.researcher_id;
        """


class ResearcherAreaLeaderResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT AS researcher_id, lattes_id::TEXT
        FROM researcher;
        """


class FatOpenalexArticleQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT article_id::TEXT, article_institution::TEXT, issn::TEXT, authors_institution::TEXT,
            abstract::TEXT, authors::TEXT, language::TEXT, citations_count::TEXT, pdf::TEXT, landing_page_url::TEXT,
            keywords::TEXT
        FROM public.openalex_article;
        """


class DimAreaLeaderQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT extra_field::TEXT AS area_leader
        FROM researcher;
        """


class DimCityQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT c.id::TEXT AS city_id, c.name::TEXT
        FROM city c;
        """


class UfmgResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT
            researcher_id::TEXT,
            full_name::TEXT,
            gender::TEXT,
            status_code::TEXT,
            work_regime::TEXT,
            job_class::TEXT,
            job_title::TEXT,
            job_rank::TEXT,
            job_reference_code::TEXT,
            academic_degree::TEXT,
            organization_entry_date::TEXT,
            last_promotion_date::TEXT,
            employment_status_description::TEXT,
            department_name::TEXT,
            career_category::TEXT,
            academic_unit::TEXT,
            unit_code::TEXT,
            function_code::TEXT,
            position_code::TEXT,
            leadership_start_date::TEXT,
            leadership_end_date::TEXT,
            current_function_name::TEXT,
            function_location::TEXT,
            registration_number::TEXT,
            ufmg_registration_number::TEXT,
            semester_reference::TEXT
        FROM ufmg.researcher;
        """


class DimDepartamentQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT dep_id::TEXT, dep_nom::TEXT, 'Escola de Engenharia'::TEXT AS institution,
            'b24e043a-c6ff-446a-a85a-14d9f944a729'::TEXT AS institution_id
        FROM ufmg.departament;
        """


class CimatecGraduateProgramStudentQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT researcher_id::TEXT, graduate_program_id::TEXT,
            EXTRACT(YEAR FROM CURRENT_DATE)::TEXT AS year
        FROM graduate_program_student;
        """


class GraduateProgramStudentYearUnnestQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT graduate_program_id::TEXT, researcher_id::TEXT, year::TEXT
        FROM graduate_program_student;
        """


class DimGraduateProgramAcronymQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT graduate_program_id::TEXT, acronym::TEXT, name::TEXT
        FROM graduate_program;
        """


class GraduateProgramResearcherYearUnnestQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT graduate_program_id::TEXT, researcher_id::TEXT, year::TEXT
        FROM graduate_program_researcher;
        """


class DimDepartamentTechnicianQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT dep_id::TEXT, technician_id::TEXT
        FROM ufmg.departament_technician;
        """


class DimDepartamentResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT dep_id::TEXT, researcher_id::TEXT
        FROM ufmg.departament_researcher;
        """


class FatGroupLeadersQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT, name::TEXT, institution::TEXT, first_leader::TEXT, first_leader_id::TEXT,
            second_leader::TEXT, second_leader_id::TEXT, area::TEXT AS "AREA", census::TEXT,
            start_of_collection::TEXT, end_of_collection::TEXT, group_identifier::TEXT, year::TEXT AS "YEAR",
            institution_name::TEXT, category::TEXT
        FROM research_group
        WHERE 1 = 1
            AND (first_leader_id IS NOT NULL OR second_leader_id IS NOT NULL);
        """


class DimResearchGroupQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT rg.id::TEXT AS group_id, TRANSLATE(rg.name, '"', '')::TEXT AS group_name,
            rg.area::TEXT, i.id::TEXT AS institution_id
        FROM public.research_group rg
        RIGHT JOIN institution i ON rg.institution ILIKE '%' || i.acronym || '%';
        """


class DimCategoryLevelCodeQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT category_level_code::TEXT
        FROM foment;
        """


class FatFomentQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT r.id::TEXT AS researcher_id, r.institution_id::TEXT, modality_code::TEXT,
            modality_name::TEXT, category_level_code::TEXT, funding_program_name::TEXT,
            aid_quantity::TEXT, scholarship_quantity::TEXT
        FROM public.foment s
            LEFT JOIN researcher r ON r.id = s.researcher_id
        WHERE s.researcher_id IS NOT NULL;
        """


class FatProductionTecnicalYearNovoCsvDbQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT
            title::TEXT, (development_year::int)::TEXT AS year, 'PATENTE'::TEXT AS type,
            p.researcher_id::TEXT, c.id::TEXT AS city_id, r.institution_id::TEXT AS institution_id,
            unaccent(LOWER(title))::TEXT AS sanitized_title, p.id::TEXT
        FROM patent p, researcher r, researcher_production rp, city c
        WHERE 1 = 1
            AND r.id = p.researcher_id
            AND rp.researcher_id = p.researcher_id
            AND rp.city = c.name

        UNION

        SELECT DISTINCT
            title::TEXT, s.year::TEXT AS year, 'SOFTWARE'::TEXT AS type, s.researcher_id::TEXT, c.id::TEXT,
            r.institution_id::TEXT, unaccent(LOWER(title))::TEXT AS sanitized_title, s.id::TEXT
        FROM software s, researcher r, researcher_production rp, city c
        WHERE 1 = 1
            AND r.id = s.researcher_id
            AND rp.researcher_id = s.researcher_id
            AND rp.city = c.name

        UNION

        SELECT DISTINCT
            title::TEXT, b.year::TEXT AS year, 'MARCA'::TEXT AS type, b.researcher_id::TEXT, c.id::TEXT,
            r.institution_id::TEXT, unaccent(LOWER(title))::TEXT AS sanitized_title, b.id::TEXT
        FROM brand b, researcher r, researcher_production rp, city c
        WHERE 1 = 1
            AND r.id = b.researcher_id
            AND rp.researcher_id = b.researcher_id
            AND rp.city = c.name

        UNION

        SELECT DISTINCT
            title::TEXT, b.year::TEXT AS year, 'RELATÓRIO TÉCNICO'::TEXT AS type, b.researcher_id::TEXT,
            c.id::TEXT, r.institution_id::TEXT, unaccent(LOWER(title))::TEXT AS sanitized_title,
            b.id::TEXT
        FROM research_report b, researcher r, researcher_production rp, city c
        WHERE 1 = 1
            AND r.id = b.researcher_id
            AND rp.researcher_id = b.researcher_id
            AND rp.city = c.name;
        """


class DimInstitutionQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT i.id::TEXT AS institution_id, name::TEXT, acronym::TEXT
        FROM  institution i;
        """


class ResearcherCityQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT researcher_id::TEXT, city::TEXT
        FROM researcher_production;
        """


class DimResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT r.name::TEXT AS researcher, r.id::TEXT AS researcher_id,
            TO_CHAR(r.last_update,'dd/mm/yyyy')::TEXT AS last_update,
            r.graduation::TEXT AS graduation, r.institution_id::TEXT, r.docente::TEXT,
            regexp_replace(r.abstract, E'[\\\\n\\\\r]+', ' - ', 'g' )::TEXT AS abstract,
            :origin || 'ResearcherData/Image?researcher_id=' || r.id::TEXT AS image,
            r.orcid::TEXT
        FROM researcher r
        WHERE r.status = True;
        """


class DimResearcherWordsQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH unified_data AS (
            SELECT researcher_id, translate(title,'-\\.:,;''', ' ') AS title
            FROM bibliographic_production
            UNION ALL
            SELECT researcher_id, translate(title,'-\\.:,;''', ' ') AS title
            FROM patent
            UNION ALL
            SELECT researcher_id, translate(title,'-\\.:,;''', ' ') AS title
            FROM brand
            UNION ALL
            SELECT researcher_id, translate(title,'-\\.:,;''', ' ') AS title
            FROM event_organization
            UNION ALL
            SELECT researcher_id, translate(title,'-\\.:,;''', ' ') AS title
            FROM software
        ),
        word_split AS (
            SELECT researcher_id, unnest(string_to_array(lower(regexp_replace(title, '[^a-zA-Z0-9\\\\s]', '', 'g')), ' ')) AS word
            FROM unified_data
        ),
        word_count AS (
            SELECT researcher_id, word, COUNT(*) AS frequency
            FROM word_split
            WHERE word <> ''
            GROUP BY researcher_id, word
        ),
        ranked_words AS (
            SELECT researcher_id, word, frequency, RANK() OVER (PARTITION BY researcher_id ORDER BY frequency DESC) AS rank
            FROM word_count
        )
        SELECT researcher_id::TEXT, STRING_AGG(word, ' | ')::TEXT AS list_of_words
        FROM ranked_words
        WHERE 1 = 1
            AND rank <= 20
            AND CHAR_LENGTH(word) > 3
            AND TRIM(word) <> ALL(:stopwords)
        GROUP BY researcher_id
        ORDER BY researcher_id;
        """


class FatSimccBibliographicProductionQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT
            title::TEXT, b.type::TEXT as tipo, b.researcher_id::TEXT, year::TEXT, i.id::TEXT AS institution_id,
            bar.qualis::TEXT, bar.periodical_magazine_name::TEXT, bar.jcr::TEXT, bar.jcr_link::TEXT,
            c.id::TEXT AS city_id, b.id::TEXT AS bibliographic_production_id,
            unaccent(LOWER(title))::TEXT AS sanitized_title, b.id::TEXT
        FROM bibliographic_production b
        LEFT JOIN bibliographic_production_article bar
            ON b.id = bar.bibliographic_production_id, researcher r
        LEFT JOIN  institution i
            ON r.institution_id = i.id
        LEFT JOIN city c
            ON r.city_id = c.id
        WHERE 1 = 1
            AND b.researcher_id IS NOT NULL
            AND r.id =  b.researcher_id
        ORDER BY
            YEAR desc;
        """


class ProductionTecnicalYearQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT researcher_id::TEXT, title::TEXT, (development_year::int)::TEXT AS year,
            'PATENT'::TEXT as type
        FROM patent
        UNION
        SELECT researcher_id::TEXT, title::TEXT, year::TEXT, 'SOFTWARE'::TEXT
        from software
        UNION
        SELECT researcher_id::TEXT, title::TEXT, year::TEXT, 'BRAND'::TEXT
        from brand
        UNION
        SELECT researcher_id::TEXT, title::TEXT, year::TEXT, 'REPORT'::TEXT
        from research_report;
        """


class ResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT r.name::TEXT AS researcher, r.id::TEXT AS researcher_id,
            TO_CHAR(r.last_update,'dd/mm/yyyy')::TEXT AS last_update,
            r.graduation::TEXT AS graduation, r.lattes_id::TEXT, extra_field::TEXT AS area_leader
        FROM  researcher r;
        """


class ArticleQualisYearInstitutionQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT
            title::TEXT, bar.qualis::TEXT AS qualis, bar.jcr::TEXT AS jcr, year::TEXT AS year, i.acronym::TEXT as institution,
            rd.city::TEXT as city, bar.jcr_link::TEXT AS jcr_link
        FROM bibliographic_production b, bibliographic_production_article bar,
            periodical_magazine pm, researcher r, institution i,
            researcher_address rd
        WHERE 1 = 1
            AND pm.id = bar.periodical_magazine_id
            AND r.id =  b.researcher_id
            AND r.institution_id = i.id
            AND b.id = bar.bibliographic_production_id
            AND rd.researcher_id = r.id
        GROUP BY title, bar.qualis, bar.jcr, year, i.acronym, rd.city,
            bar.jcr_link
        ORDER BY qualis desc;
        """


class ProductionResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT r.name::TEXT AS researcher, r.id::TEXT AS researcher_id,
            rp.articles::TEXT AS articles, rp.book_chapters::TEXT AS book_chapters,
            rp.book::TEXT AS book, rp.work_in_event::TEXT AS work_in_event,
            rp.great_area::TEXT AS great_area, rp.area_specialty::TEXT AS area_specialty,
            r.graduation::TEXT as graduation, rp.city::TEXT as city
        FROM researcher_production rp, researcher r
        WHERE r.id = rp.researcher_id;
        """


class ArticleQualisYearQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT
            title::TEXT, bar.qualis::TEXT, year::TEXT, r.id::TEXT AS researcher_id,
            r.name::TEXT AS researcher, i.name::TEXT AS institution, c.name::TEXT AS city,
            pm.name::TEXT AS name_magazine, pm.issn::TEXT AS issn, bar.jcr::TEXT as jcr,
            bar.jcr_link::TEXT as jcr_link, b.type::TEXT as type
        FROM bibliographic_production b
            LEFT JOIN (bibliographic_production_article bar
                LEFT JOIN periodical_magazine pm
                    ON pm.id = bar.periodical_magazine_id)
                ON b.id = bar.bibliographic_production_id,
            researcher r
            LEFT JOIN institution i ON i.id = r.institution_id
            LEFT JOIN city c ON c.id = r.city_id
        WHERE r.id =  b.researcher_id;
        """


class ProductionYearDistinctQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT
            year::TEXT, title::TEXT, type::TEXT AS tipo, i.acronym::TEXT AS institution
        FROM bibliographic_production AS b, institution i, researcher r
        WHERE 1 = 1
            AND r.id = b.researcher_id
            AND r.institution_id = i.id
        GROUP BY year, title, tipo, i.acronym;
        """


class ProductionYearQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT
            b.title::TEXT,
            b.type::TEXT AS tipo,
            b.researcher_id::TEXT,
            b.year::TEXT AS year,
            i.name::TEXT AS institution
        FROM bibliographic_production AS b
        LEFT JOIN researcher r ON r.id = b.researcher_id
        LEFT JOIN institution i ON i.id = r.institution_id
        WHERE b.researcher_id IS NOT NULL
        GROUP BY b.title, b.type, b.researcher_id, b.year, i.name
        ORDER BY year, tipo DESC;
        """


class ProductionCoauthorsCsvDbQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH gp_cte AS (
            SELECT
                researcher_id,
                graduate_program_id,
                MAX(year) AS year
            FROM graduate_program_researcher
            GROUP BY
                researcher_id,
                graduate_program_id
        ),

        base AS (
            SELECT
                a.id,
                a.researcher_id,
                a.doi,
                a.title,
                a.year,
                a.type,
                ba.qualis
            FROM bibliographic_production a
            LEFT JOIN bibliographic_production_article ba
                ON ba.bibliographic_production_id = a.id
        )

        SELECT
            (COUNT(*) + 1)::TEXT AS qtd,
            base.doi::TEXT,
            base.title::TEXT,
            base.qualis::TEXT,
            base.year::TEXT,
            gp.graduate_program_id::TEXT,
            gp.year::TEXT AS year_pos,
            base.type::TEXT
        FROM base
        JOIN gp_cte gp
            ON gp.researcher_id = base.researcher_id
        WHERE EXISTS (
            SELECT 1
            FROM base b
            WHERE b.researcher_id = base.researcher_id
            AND (
                    (b.doi IS NOT NULL AND b.doi = base.doi)
                OR (b.title = base.title)
            )
            AND b.id <> base.id
        )
        GROUP BY
            base.doi,
            base.title,
            base.qualis,
            base.year,
            gp.graduate_program_id,
            gp.year,
            base.type
        HAVING COUNT(*) > 1;
        """


class FatResearcherIndProdQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT researcher_id::TEXT, year::TEXT, ind_prod_article::TEXT, ind_prod_book::TEXT,
            ind_prod_book_chapter::TEXT, ind_prod_granted_patent::TEXT,
            ind_prod_not_granted_patent::TEXT, ind_prod_software::TEXT, ind_prod_report::TEXT,
            ind_prod_guidance::TEXT
        FROM researcher_ind_prod;
        """


class GraduateProgramIndProdQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT graduate_program_id::TEXT, year::TEXT, ind_prod_article::TEXT, ind_prod_book::TEXT,
            ind_prod_book_chapter::TEXT, ind_prod_granted_patent::TEXT,
            ind_prod_not_granted_patent::TEXT, ind_prod_software::TEXT, ind_prod_report::TEXT,
            ind_prod_guidance::TEXT
        FROM graduate_program_ind_prod;
        """


class ResearcherProductionNovoCsvDbQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT title::TEXT, qualis::TEXT, year::TEXT, r.id::TEXT as researcher_id, r.name::TEXT as researcher,
            bar.periodical_magazine_name::TEXT as name_magazine, issn::TEXT AS issn,
            jcr::TEXT as jcr, jcr_link::TEXT, b.type::TEXT as type
        FROM bibliographic_production b
            LEFT JOIN  bibliographic_production_article bar
                ON b.id = bar.bibliographic_production_id,
                researcher r
        WHERE r.id = b.researcher_id;
        """


class ArticleDistinctNovoCsvDbQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT
            title::TEXT, bar.qualis::TEXT, bar.jcr::TEXT, b.year::TEXT as year,
            gp.graduate_program_id::TEXT as graduate_program_id, b.year::TEXT as year_pos,
            periodical_magazine.name::TEXT AS type
        FROM bibliographic_production b
            LEFT JOIN bibliographic_production_article bar
                ON b.id = bar.bibliographic_production_id
            LEFT JOIN periodical_magazine
                ON periodical_magazine.id = bar.periodical_magazine_id,
            researcher r, graduate_program_researcher gpr, graduate_program gp
        WHERE gpr.graduate_program_id = gp.graduate_program_id
            AND gpr.researcher_id = r.id
            AND r.id = b.researcher_id
            AND b.year::INT = gpr.year
            AND b.type = 'ARTICLE'
        ORDER BY qualis desc;
        """


class ProductionDistinctNovoCsvDbQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT
            title::TEXT, qualis::TEXT, jcr::TEXT, b.year::TEXT AS year,
            gp.graduate_program_id::TEXT AS graduate_program_id, b.year::TEXT as year_pos,
            b.type::TEXT AS type
        FROM bibliographic_production b
            LEFT JOIN  bibliographic_production_article bar
                ON b.id = bar.bibliographic_production_id,
            researcher r, graduate_program_researcher gpr, graduate_program gp
        WHERE gpr.graduate_program_id = gp.graduate_program_id
            AND gpr.researcher_id = r.id
            AND r.id = b.researcher_id
            AND b.year::INT = gpr.year
        order by qualis desc;
        """


class CimatecGraduateProgramResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT ON (researcher_id, graduate_program_id)
            researcher_id::TEXT,
            graduate_program_id::TEXT,
            2026 AS year,
            type_::TEXT
        FROM graduate_program_researcher
        ORDER BY researcher_id, graduate_program_id;
        """


class CimatecGraduateProgramQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT gp.graduate_program_id::TEXT, gp.code::TEXT, gp.name::TEXT, gp.area::TEXT, gp.modality::TEXT,
            gp.type::TEXT, gp.rating::TEXT, i.id::TEXT AS institution_id, i.name::TEXT AS institution,
            gp.city::TEXT
        FROM graduate_program gp
            LEFT JOIN institution i
                ON i.id = gp.institution_id
        WHERE visible IS True;
        """


class DimResearchProjectQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT, researcher_id::TEXT, start_year::TEXT, end_year::TEXT, agency_code::TEXT, agency_name::TEXT,
            TRANSLATE(project_name, ',', ' ')::TEXT AS project_name, status::TEXT, nature::TEXT,
            number_undergraduates::TEXT, TRANSLATE(description, ',', ' ')::TEXT AS description,
            number_specialists::TEXT, number_academic_masters::TEXT, number_phd::TEXT
        FROM research_project;
        """


class FatResearchProjectFomentQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT project_id::TEXT, agency_name::TEXT, agency_code::TEXT, nature::TEXT
        FROM research_project_foment;
        """


class DimBibliographicProductionTermsQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return r"""
        WITH unified_data AS (
            SELECT id::TEXT, 'BIBLIOGRAPHIC_PRODUCTION' AS type_,
                translate(title,'-\.:,;''', ' ') AS title
            FROM bibliographic_production
        ),
        word_split AS (
            SELECT id, type_,
                unnest(
                string_to_array(
                lower(
                regexp_replace(title, '[^a-zA-Z0-9\s]', '', 'g')), ' ')) AS word
            FROM unified_data
        ),
        word_count AS (
            SELECT id, type_, word, COUNT(*) AS frequency
            FROM word_split
            WHERE word <> ''
            GROUP BY id, type_, word
        ),
        ranked_words AS (
            SELECT id, type_, word, frequency,
            RANK() OVER (PARTITION BY id ORDER BY frequency DESC) AS rank
            FROM word_count
        )
        SELECT id, type_, UNNEST(ARRAY_AGG(ranked_words.word)) AS term
        FROM ranked_words
        WHERE 1 = 1
            AND rank <= 20
            AND CHAR_LENGTH(word) > 3
            AND TRIM(word) <> ALL(:stopwords)
        GROUP BY id, type_
        ORDER BY id;
        """


class DimTecnicalProductionTermsQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return r"""
WITH unified_data AS (
    SELECT id::TEXT, 'PATENT' AS type_,
        translate(title,'-\.:,;''', ' ') AS title
    FROM patent
    UNION ALL
    SELECT id::TEXT, 'BRAND', translate(title,'-\.:,;''', ' ') AS title
    FROM brand
    UNION ALL
    SELECT id::TEXT, 'SOFTWARE', translate(title,'-\.:,;''', ' ') AS title
    FROM software
),
word_split AS (
    SELECT id, type_,
        unnest(
        string_to_array(
        lower(
        regexp_replace(title, '[^a-zA-Z0-9\s]', '', 'g')), ' ')) AS word
    FROM unified_data
),
word_count AS (
    SELECT id, type_, word, COUNT(*) AS frequency
    FROM word_split
    WHERE word <> ''
    GROUP BY id, type_, word
),
ranked_words AS (
    SELECT id, type_, word, frequency,
        RANK() OVER (PARTITION BY id ORDER BY frequency DESC) AS rank
    FROM word_count
)
SELECT id, type_, UNNEST(ARRAY_AGG(ranked_words.word)) AS term
FROM ranked_words
WHERE 1 = 1
    AND rank <= 20
    AND CHAR_LENGTH(word) > 3
    AND TRIM(word) <> ALL(:stopwords)
GROUP BY id, type_
ORDER BY id;
        """


class DimLogsRoutineQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT (unnest(enum_range(NULL::routine_type)))::TEXT AS routine_type;
        """


class FatLogsRoutineQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT DISTINCT ON (type) type::TEXT, error::TEXT, detail::TEXT,
            created_at::TEXT
        FROM logs.routine
        ORDER BY type, created_at DESC;
        """


class FatEventOrganizationQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT, title::TEXT, promoter_institution::TEXT, nature::TEXT,
            researcher_id::TEXT, local::TEXT, duration_in_weeks::TEXT, year::TEXT
        FROM public.event_organization;
        """


class FatParticipationEventsQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT, title::TEXT, event_name::TEXT, nature::TEXT, form_participation::TEXT,
            type_participation::TEXT, researcher_id::TEXT, year::TEXT
        FROM public.participation_events;
        """


class MaterializedVisionQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT AS researcher_id, abstract::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(abstract, $$-\".:,;'$$, ' ')))::TEXT
            AS normalized_search_term, 'ABSTRACT'::TEXT AS type,
            (EXTRACT(YEAR FROM last_update))::TEXT AS year
        FROM researcher
            UNION
        SELECT researcher_id::TEXT, title::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(title, $$-\\.:,;'$$, ' ')))::TEXT
            AS normalized_search_term, 'PATENT'::TEXT AS type, development_year::TEXT
        FROM patent
            UNION
        SELECT researcher_id::TEXT, title::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(title, $$-\\.:,;'$$, ' ')))::TEXT
            AS normalized_search_term, type::TEXT AS type, year::TEXT AS year_
        FROM bibliographic_production
            UNION
        SELECT researcher_id::TEXT, title::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(title, $$-\\.:",;'$$, ' ')))::TEXT
            AS normalized_search_term, 'REPORT'::TEXT AS type, year::TEXT AS year
        FROM research_report
            UNION
        SELECT researcher_id::TEXT, title::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(title, $$-\\.:,",;'$$, ' ')))::TEXT
                AS normalized_search_term, 'SOFTWARE'::TEXT AS type, year::TEXT AS year
        FROM software
            UNION
        SELECT researcher_id::TEXT, title::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(title, $$-\\.:,;'$$, ' ')))::TEXT
            AS normalized_search_term, 'GUIDANCE'::TEXT AS type, year::TEXT AS year
        FROM guidance
            UNION
        SELECT researcher_id::TEXT, title::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(title, $$-\\.:,;'$$, ' ')))::TEXT
            AS normalized_search_term, 'BRAND'::TEXT AS type, year::TEXT AS year
        FROM brand
            UNION
        SELECT researcher_id::TEXT, title::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(title, $$-\\.:,;'$$, ' ')))::TEXT
            AS normalized_search_term, 'EVENT_ORGANIZATION'::TEXT AS type,
            year::TEXT AS year
        FROM public.event_organization
            UNION
        SELECT researcher_id::TEXT, project_name::TEXT AS search_term,
            UNACCENT(LOWER(TRANSLATE(project_name, $$-\".:,;'$$, ' ')))::TEXT
            AS normalized_search_term, 'RESEARCH_PROJECT'::TEXT AS type, start_year::TEXT AS start_year
        FROM public.research_project;
        """


class FatArticleKeywordUnderscoreQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH unified_data AS (
            SELECT bp.title AS title_, REGEXP_REPLACE(TRANSLATE(bp.title, $$-\\.:,;$$, ' '), '<[^>]*>', '', 'g') AS title, bp.researcher_id
            FROM bibliographic_production bp
            WHERE type = 'ARTICLE'
        ),
        split_words AS (
            SELECT title_ AS title, regexp_split_to_table(title, '\\\\s+') AS word, researcher_id
            FROM unified_data
        ),
        normalized_words AS (
            SELECT title, lower(trim(word)) AS word, researcher_id
            FROM split_words
            WHERE word <> '' AND CHAR_LENGTH(word) > 3 AND lower(trim(word)) <> ALL(:stopwords)
        )
        SELECT title::TEXT, word::TEXT, researcher_id::TEXT AS researcher_id
        FROM normalized_words
        ORDER BY title;
        """


class DimArticleKeywordQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH unified_data AS (
            SELECT REGEXP_REPLACE(TRANSLATE(title, $$-\\.:,;$$, ' '), '<[^>]*>', '', 'g') AS title
            FROM bibliographic_production
            WHERE type = 'ARTICLE'
        ),
        split_words AS (
            SELECT regexp_split_to_table(title, '\\\\s+') AS word
            FROM unified_data
        ),
        normalized_words AS (
            SELECT lower(trim(word)) AS word, COUNT(*) AS frequency
            FROM split_words
            WHERE word <> '' AND CHAR_LENGTH(word) > 3 AND lower(trim(word)) <> ALL(:stopwords)
            GROUP BY word
            HAVING COUNT(*) > 5
        )
        SELECT word::TEXT, frequency::TEXT
        FROM normalized_words
        ORDER BY frequency DESC;
        """


class FatArticleCoAuthorshipQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT title::TEXT, (UNNEST(ARRAY_AGG(researcher_id)))::TEXT AS researcher_id
        FROM bibliographic_production
        WHERE type = 'ARTICLE'
        GROUP BY title
        HAVING COUNT(*) > 1
        ORDER BY title;
        """


class FatKeywordsCooccurrencesQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH unified_data AS (
            SELECT REGEXP_REPLACE(TRANSLATE(title, $$-\\.:,;$$, ' '), '<[^>]*>', '', 'g') AS title
            FROM bibliographic_production
            WHERE type = 'ARTICLE'
        ),
        tokenized_titles AS (
            SELECT ROW_NUMBER() OVER () AS title_id,
                regexp_split_to_array(lower(trim(REGEXP_REPLACE(TRANSLATE(title, $$-\\.:,;$$, ' '), '<[^>]*>', '', 'g'))), '\\\\s+') AS words
            FROM unified_data
        ),
        filtered_tokens AS (
            SELECT title_id,
                unnest(words) AS word
            FROM tokenized_titles
        ),
        cleaned_tokens AS (
            SELECT title_id,
                lower(trim(word)) AS word
            FROM filtered_tokens
            WHERE word <> '' AND CHAR_LENGTH(word) > 3 AND lower(trim(word)) <> ALL(:stopwords)
        ),
        cooccurrences AS (
            SELECT LEAST(a.word, b.word) AS word1,
                GREATEST(a.word, b.word) AS word2
            FROM cleaned_tokens a
            JOIN cleaned_tokens b
                ON a.title_id = b.title_id AND a.word <> b.word
        ),
        cooc_count AS (
            SELECT word1, word2, COUNT(*) AS frequency
            FROM cooccurrences
            GROUP BY word1, word2
        )

        SELECT word1::TEXT, word2::TEXT, frequency::TEXT
        FROM cooc_count
        ORDER BY frequency DESC;
        """


class FatCoAuthorshipQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH co_articles AS (
            SELECT title, ARRAY_AGG(researcher_id) AS co_authors
            FROM bibliographic_production
            WHERE type = 'ARTICLE'
            GROUP BY title
        ),
        co_authors AS (
            SELECT co_articles.title, bp.researcher_id, UNNEST(co_authors) AS co_author
            FROM bibliographic_production bp
            INNER JOIN co_articles ON co_articles.title = bp.title
        )
        SELECT co_authors.title::TEXT, co_authors.researcher_id::TEXT, co_authors.co_author::TEXT
        FROM co_authors
        WHERE co_authors.researcher_id != co_authors.co_author;
        """


class GuidanceQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH co_supervisors AS (
            SELECT DISTINCT ON (gcs.guidance_tracking_id)
                gcs.guidance_tracking_id,
                gcs.co_supervisor_researcher_id
            FROM admin.guidance_co_supervisors gcs
            ORDER BY gcs.guidance_tracking_id
        )
        SELECT
            gt.id::TEXT AS id,
            r_student.lattes_id::TEXT AS student_lattes_id,
            r_supervisor.lattes_id::TEXT AS supervisor_lattes_id,
            r_co.lattes_id::TEXT AS co_supervisor_lattes_id, 
            gt.graduate_program_id::TEXT AS graduate_program_id,
            gt.start_date::TEXT AS start_date,
            gt.planned_date_project::TEXT AS planned_date_project,
            gt.done_date_project::TEXT AS done_date_project,
            gt.planned_date_qualification::TEXT AS planned_date_qualification,
            gt.done_date_qualification::TEXT AS done_date_qualification,
            gt.planned_date_conclusion::TEXT AS planned_date_conclusion,
            gt.done_date_conclusion::TEXT AS done_date_conclusion,
            r_student.name::TEXT AS student_name,
            r_supervisor.name::TEXT AS supervisor_name,
            r_co.name::TEXT AS co_name,
            gp.type::TEXT AS type
        FROM public.guidance_tracking gt
        LEFT JOIN admin.researcher r_student
            ON r_student.researcher_id = gt.student_researcher_id
        LEFT JOIN admin.researcher r_supervisor
            ON r_supervisor.researcher_id = gt.supervisor_researcher_id
        LEFT JOIN admin.graduate_program gp
            ON gp.graduate_program_id = gt.graduate_program_id
        LEFT JOIN co_supervisors cos
            ON cos.guidance_tracking_id = gt.id
        LEFT JOIN admin.researcher r_co
            ON r_co.researcher_id = cos.co_supervisor_researcher_id
        WHERE gt.deleted_at IS NULL;
        """


class GuidanceResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT AS researcher_id, lattes_id::TEXT
        FROM researcher;
        """


class DimTagsQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT, name::TEXT, color_code::TEXT FROM admin.tags;
        """


class FatTagsQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT guidance_tracking_id::TEXT, tag_id::TEXT
        FROM admin.guidance_tags;
        """


class DimSdgQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT id::TEXT, number::TEXT, name::TEXT FROM sdg;
        """


class FatSdgArticlesQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT
            bp.title::TEXT,
            bp.researcher_id::TEXT,
            sa.sdg_id::TEXT,
            bp.year::TEXT,
            bpa.qualis::TEXT,
            bpa.periodical_magazine_id::TEXT,
            bpa.periodical_magazine_name::TEXT
        FROM bibliographic_production bp
        JOIN sdg_alignment sa ON bp.id = sa.reference_id
        LEFT JOIN bibliographic_production_article bpa ON bpa.bibliographic_production_id = bp.id
        WHERE sa.type = 'ARTICLE';
        """


class FatSdgAlignmentResearcherQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH sdg_counts AS (
            SELECT 
                bp.researcher_id, 
                s.number AS sdg_number,
                s.name AS sdg_name,
                COUNT(*) AS total_articles
            FROM bibliographic_production bp
            JOIN sdg_alignment sa ON bp.id = sa.reference_id
            JOIN sdg s ON sa.sdg_id = s.id
            GROUP BY bp.researcher_id, s.number, s.name
        ),
        ranking AS (
            SELECT 
                researcher_id, 
                sdg_number,
                sdg_name,
                total_articles,
                SUM(total_articles) OVER(PARTITION BY researcher_id) AS researcher_total,
                RANK() OVER(PARTITION BY researcher_id ORDER BY total_articles DESC) as rank
            FROM sdg_counts
        )
        SELECT 
            researcher_id::TEXT, 
            sdg_number::TEXT,
            sdg_name::TEXT AS primary_sdg_name, 
            total_articles::TEXT,
            ROUND((total_articles * 100.0) / researcher_total, 2)::TEXT AS percentage
        FROM ranking
        WHERE rank = 1;
        """


class IndGuidanceOriQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH Masters AS (
            SELECT 
                gt.graduate_program_id,
                EXTRACT(YEAR FROM gt.done_date_conclusion) AS year_val,
                COUNT(*) AS qty
            FROM public.guidance_tracking gt
            JOIN admin.graduate_program gp ON gt.graduate_program_id = gp.graduate_program_id
            WHERE gp.type = 'MESTRADO' 
            AND gt.done_date_conclusion IS NOT NULL
            GROUP BY gt.graduate_program_id, EXTRACT(YEAR FROM gt.done_date_conclusion)
        ),
        Doctorate AS (
            SELECT 
                gt.graduate_program_id,
                EXTRACT(YEAR FROM gt.done_date_conclusion) AS year_val,
                COUNT(*) AS qty
            FROM public.guidance_tracking gt
            JOIN admin.graduate_program gp ON gt.graduate_program_id = gp.graduate_program_id
            WHERE gp.type = 'DOUTORADO' 
            AND gt.done_date_conclusion IS NOT NULL
            GROUP BY gt.graduate_program_id, EXTRACT(YEAR FROM gt.done_date_conclusion)
        ),
        Permanent AS (
            SELECT 
                graduate_program_id,
                year AS year_val,
                COUNT(*) AS qty
            FROM admin.graduate_program_researcher
            WHERE type_ = 'PERMANENTE'
            GROUP BY graduate_program_id, year
        )
        SELECT 
            p.graduate_program_id::TEXT,
            p.year_val::TEXT AS year,
            COALESCE(m.qty, 0)::TEXT AS masters_defenses,
            COALESCE(d.qty, 0)::TEXT AS doctorate_defenses,
            p.qty::TEXT AS permanent_researchers,
            ((COALESCE(m.qty, 0) + (2.0 * COALESCE(d.qty, 0))) / NULLIF(p.qty, 0))::TEXT AS ind_ori
        FROM Permanent p
        LEFT JOIN Masters m ON p.graduate_program_id = m.graduate_program_id AND p.year_val = m.year_val
        LEFT JOIN Doctorate d ON p.graduate_program_id = d.graduate_program_id AND p.year_val = d.year_val
        ORDER BY p.graduate_program_id, p.year_val;
        """


class IndGuidanceCoautProgQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT 
            gpr.graduate_program_id::TEXT,
            r.researcher_id::TEXT
        FROM admin.researcher r
        INNER JOIN admin.graduate_program_researcher gpr
            ON gpr.researcher_id = r.researcher_id;
        """


class IndGuidanceCoautProdQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT researcher_id::TEXT, doi::TEXT AS identifier, year::TEXT, 'ARTICLE'::TEXT AS type
        FROM bibliographic_production
        WHERE type = 'ARTICLE'

        UNION ALL

        SELECT bp.researcher_id::TEXT, bpb.isbn::TEXT AS identifier, bp.year::TEXT, 'BOOK'::TEXT AS type
        FROM bibliographic_production bp
        LEFT JOIN bibliographic_production_book bpb
            ON bpb.bibliographic_production_id = bp.id
        WHERE bp.type = 'BOOK'

        UNION ALL

        SELECT bp.researcher_id::TEXT, bpc.isbn::TEXT AS identifier, bp.year::TEXT, 'BOOK_CHAPTER'::TEXT AS type
        FROM bibliographic_production bp
        LEFT JOIN bibliographic_production_book_chapter bpc
            ON bpc.bibliographic_production_id = bp.id
        WHERE bp.type = 'BOOK_CHAPTER';
        """


class IndGuidanceDistoriQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        WITH ConcludingResearchers AS (
            SELECT 
                gt.graduate_program_id,
                EXTRACT(YEAR FROM gt.done_date_conclusion) AS year_val,
                COUNT(DISTINCT gt.supervisor_researcher_id) AS concluding_qty
            FROM public.guidance_tracking gt
            JOIN admin.graduate_program_researcher gpr 
                ON gt.supervisor_researcher_id = gpr.researcher_id
                AND gt.graduate_program_id = gpr.graduate_program_id
                AND EXTRACT(YEAR FROM gt.done_date_conclusion) = gpr.year
            WHERE gt.done_date_conclusion IS NOT NULL
            AND gpr.type_ = 'PERMANENTE'
            GROUP BY gt.graduate_program_id, EXTRACT(YEAR FROM gt.done_date_conclusion)
        ),
        Permanent AS (
            SELECT 
                graduate_program_id,
                year AS year_val,
                COUNT(DISTINCT researcher_id) AS total_qty
            FROM admin.graduate_program_researcher
            WHERE type_ = 'PERMANENTE'
            GROUP BY graduate_program_id, year
        )
        SELECT 
            p.graduate_program_id::TEXT,
            p.year_val::TEXT AS year,
            COALESCE(c.concluding_qty, 0)::TEXT AS concluding_researchers,
            p.total_qty::TEXT AS permanent_researchers,
            ((COALESCE(c.concluding_qty, 0) * 1.0) / NULLIF(p.total_qty, 0))::TEXT AS ind_dist_ori
        FROM Permanent p
        LEFT JOIN ConcludingResearchers c ON p.graduate_program_id = c.graduate_program_id AND p.year_val = c.year_val
        ORDER BY p.graduate_program_id, p.year_val;
        """


class FatGuidanceHistoryQuery(BaseQuery):
    @override
    def build_sql(self) -> str:
        return """
        SELECT 
            r_student.name::TEXT AS student_name,
            r_student.lattes_id::TEXT AS student_lattes_id,
            r_supervisor.lattes_id::TEXT AS supervisor_lattes_id,
            gt.start_date::TEXT AS start_date,
            gt.planned_date_project::TEXT AS planned_date_project,
            gt.done_date_project::TEXT AS done_date_project,
            gt.planned_date_qualification::TEXT AS planned_date_qualification,
            gt.done_date_qualification::TEXT AS done_date_qualification,
            gt.planned_date_conclusion::TEXT AS planned_date_conclusion,
            gt.done_date_conclusion::TEXT AS done_date_conclusion
        FROM public.guidance_tracking gt
        INNER JOIN admin.researcher r_student
            ON gt.student_researcher_id = r_student.researcher_id
        LEFT JOIN admin.researcher r_supervisor
            ON gt.supervisor_researcher_id = r_supervisor.researcher_id
        WHERE gt.deleted_at IS NULL;
        """
