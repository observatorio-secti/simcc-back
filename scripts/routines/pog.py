import argparse
import time

from sqlalchemy import text

from simcc.core.db.database import get_sync_session
from simcc.core.logging import logger
from simcc.core.logging.events import (
    routine_step_finished,
    routine_step_started,
)

items_found = 0
items_succeeded = 0
items_failed = 0


def main(researcher_ids=None, lattes_ids=None):
    global items_found, items_succeeded, items_failed
    session = next(get_sync_session())
    start_time = time.perf_counter()

    sql_steps = [
        (
            'clean_bibliographic_year',
            "UPDATE bibliographic_production SET year = NULL WHERE YEAR !~ '^\\d+$';",
        ),
        (
            'fix_specific_qualis',
            "UPDATE bibliographic_production_article ba SET qualis = 'A4' WHERE ba.issn = '17412242';",
        ),
        (
            'set_docente_flag',
            'UPDATE researcher SET docente = true WHERE id IN (SELECT researcher_id FROM graduate_program_researcher);',
        ),
        (
            'update_jcr_eissn',
            """
            UPDATE bibliographic_production_article p
            SET jcr=(subquery.jif2019), jcr_link=url_revista
            FROM (SELECT jif2019, eissn, url_revista FROM JCR) AS subquery
            WHERE translate(subquery.eissn,'-','') = p.issn
        """,
        ),
        (
            'update_jcr_issn',
            """
            UPDATE bibliographic_production_article p
            SET jcr = (subquery.jif2019), jcr_link=url_revista
            FROM (SELECT jif2019, issn, url_revista FROM JCR) AS subquery
            WHERE translate(subquery.issn,'-','') = p.issn;
        """,
        ),
        (
            'cast_year_integer',
            'UPDATE bibliographic_production SET YEAR_ = YEAR::INTEGER',
        ),
        (
            'clean_title_quotes',
            "UPDATE bibliographic_production SET title = translate(title, '''', ' ')",
        ),
        (
            'update_periodical_jcr',
            """
            UPDATE periodical_magazine pm
            SET JCR = jcr.JIF2019
            FROM jcr
            WHERE REPLACE(jcr.issn, '-', '') = pm.issn
            AND pm.issn IS NOT NULL;
        """,
        ),
        (
            'split_great_area',
            "UPDATE researcher_production SET great_area_ = STRING_TO_ARRAY(great_area, ';');",
        ),
        (
            'deduplicate_prof_experience',
            """
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY researcher_id, enterprise, start_year, end_year ORDER BY id) AS rn
                FROM public.researcher_professional_experience
            )
            DELETE FROM public.researcher_professional_experience WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """,
        ),
        (
            'clean_guidance_html_tags',
            "UPDATE guidance SET title = regexp_replace(title, '<a[^>]*>|</a>', '', 'gi');",
        ),
        (
            'link_group_leaders',
            """
            UPDATE research_group rg SET second_leader_id = r.id FROM researcher r WHERE rg.second_leader = r.name;
            UPDATE research_group rg SET first_leader_id = r.id FROM researcher r WHERE rg.first_leader = r.name;
        """,
        ),
        (
            'fix_gp_researchers',
            """
            WITH distinct_researchers AS (
    SELECT DISTINCT ON (graduate_program_id, researcher_id)
        graduate_program_id,
        researcher_id,
        type_,
        tag
    FROM graduate_program_researcher
    ORDER BY graduate_program_id, researcher_id, year DESC
),
years AS (
    SELECT generate_series(2012, 2026) AS year
)
INSERT INTO graduate_program_researcher (
    graduate_program_id,
    researcher_id,
    year,
    type_,
    tag
)
SELECT 
    r.graduate_program_id,
    r.researcher_id,
    y.year,
    r.type_,
    r.tag
FROM distinct_researchers r
CROSS JOIN years y
ON CONFLICT (graduate_program_id, researcher_id, year) DO NOTHING;
        """,
        ),
    ]

    items_found = (
        len(sql_steps) + 1
    )  # 12 static SQLs + 1 quadrennial calculation

    try:
        succeeded_steps = 0
        for step_name, sql_str in sql_steps:
            routine_step_started(step_name)
            session.execute(text(sql_str))
            routine_step_finished(step_name)
            succeeded_steps += 1

        # Step 13: Quadrennial updates
        routine_step_started('update_quadrennial')
        quadrennials = [
            {'start_year': 2013, 'end_year': 2016},
            {'start_year': 2017, 'end_year': 2020},
            {'start_year': 2021, 'end_year': 2024},
            {'start_year': 2025, 'end_year': 2028},
        ]
        case_clauses = []
        for q in quadrennials:
            start = q['start_year']
            end = q['end_year']
            case_clauses.append(
                f"WHEN bp.year_ BETWEEN {start} AND {end} THEN '{start}/{end}'"
            )
        case_sql = ' '.join(case_clauses)
        update_quadrennial_sql = f"""
            UPDATE bibliographic_production_article bpa
            SET quadrennial = CASE
                {case_sql}
                ELSE NULL
            END
            FROM bibliographic_production bp
            WHERE bpa.bibliographic_production_id = bp.id;
        """
        session.execute(text(update_quadrennial_sql))
        routine_step_finished('update_quadrennial')
        succeeded_steps += 1

        session.commit()
        items_succeeded = succeeded_steps
        items_failed = items_found - items_succeeded
        duration = time.perf_counter() - start_time
    except Exception as e:
        items_succeeded = (
            succeeded_steps if 'succeeded_steps' in locals() else 0
        )
        items_failed = items_found - items_succeeded
        logger.error(f'Error executing pog routine: {e}')
        session.rollback()
        duration = time.perf_counter() - start_time
        raise e


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--researcher-ids',
        nargs='+',
        type=str,
        default=None,
    )
    parser.add_argument(
        '--lattes-ids',
        nargs='+',
        type=str,
        default=None,
    )
    args = parser.parse_args()

    main(researcher_ids=args.researcher_ids, lattes_ids=args.lattes_ids)
