from simcc.queries.research_group_query import (
    ResearchGroupCountQuery,
    ResearchGroupQuery,
    ResearchLinesQuery,
)


async def list_research_groups(session, filters):
    query = ResearchGroupQuery(session)
    query.apply_filters(filters)
    query.apply_pagination(filters)
    return await query.execute()


async def list_research_lines(session, group_id):
    query = ResearchLinesQuery(session)
    query.apply_filters({'group_id': group_id} if group_id else None)
    return await query.execute()


async def count_research_groups_by_area(session, filters=None):
    query = ResearchGroupCountQuery(session)
    if filters:
        query.apply_filters(filters)
    return await query.execute()
