from simcc.repositories import research_group_repo


async def list_research_groups(session, filters):
    return await research_group_repo.list_research_groups(session, filters)


async def list_research_lines(session, group_id):
    return await research_group_repo.list_research_lines(session, group_id)


async def count_research_groups_by_area(session, filters=None):
    return await research_group_repo.count_research_groups_by_area(
        session, filters
    )
