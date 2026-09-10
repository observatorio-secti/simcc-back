from typing import Set

from simcc.queries.base import BaseQuery


class ResearchGroupQuery(BaseQuery):
    SUPPORTED_FILTERS: Set[str] = {'group_id', 'institution_id'}

    def _apply_group_id_filter(self, value):
        self.params['group_id'] = value
        self.filters_sql.append('AND rg.id = :group_id')

    def _apply_institution_id_filter(self, value):
        self.params['institution_id'] = value
        self.filters_sql.append('AND i.id = :institution_id')

    def build_sql(self) -> str:
        filters = ' '.join(self.filters_sql)
        return f"""
        SELECT
            rg.id,
            rg.name,
            rg.institution || ' - ' || i.name AS institution,
            rg.first_leader,
            rg.first_leader_id,
            rg.second_leader,
            rg.second_leader_id,
            rg.area,
            rg.census,
            rg.start_of_collection,
            rg.end_of_collection,
            rg.group_identifier,
            rg.year,
            rg.institution_name,
            rg.category
        FROM research_group rg
            INNER JOIN institution i ON i.acronym = rg.institution
        WHERE (
            rg.first_leader_id IS NOT NULL
            OR rg.second_leader_id IS NOT NULL
        )
            AND i.acronym IS NOT NULL
            {filters}
        ORDER BY rg.name
        {self.pagination_sql}
        """


class ResearchLinesQuery(BaseQuery):
    SUPPORTED_FILTERS: Set[str] = {'group_id'}

    def _apply_group_id_filter(self, value):
        self.params['group_id'] = value
        self.filters_sql.append('AND rl.research_group_id = :group_id')

    def build_sql(self) -> str:
        filters = ' '.join(self.filters_sql)
        return f"""
        SELECT
            rl.title AS line,
            rl.objective,
            rl.keyword AS keywords,
            rl.predominant_major_area AS major_area,
            rl.predominant_area AS area,
            rl.year
        FROM
            research_lines rl
        WHERE 1 = 1
            {filters}
        """


class ResearchGroupCountQuery(BaseQuery):
    SUPPORTED_FILTERS: Set[str] = {'group_id', 'institution_id'}

    def _apply_group_id_filter(self, value):
        self.params['group_id'] = value
        self.filters_sql.append('AND rg.id = :group_id')

    def _apply_institution_id_filter(self, value):
        self.params['institution_id'] = value
        self.filters_sql.append('AND i.id = :institution_id')

    def build_sql(self) -> str:
        filters = ' '.join(self.filters_sql)
        return f"""
        SELECT
            rg.area,
            COUNT(*) AS count
        FROM
            public.research_group rg
            INNER JOIN institution i ON i.acronym = rg.institution
        WHERE (
            rg.first_leader_id IS NOT NULL
            OR rg.second_leader_id IS NOT NULL
        )
            AND i.acronym IS NOT NULL
            {filters}
        GROUP BY rg.area
        ORDER BY count DESC;
        """
