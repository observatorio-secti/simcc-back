from simcc.v1.queries.graduate_program_query import (
    GraduateProgramArticleProductionQuery,
    GraduateProgramQuery,
    GraduateProgramResearcherQuery,
    ResearchLinesQuery,
)


async def list_graduate_programs(session, filters):
    query = GraduateProgramQuery(session)
    query.apply_filters(filters)
    return await query.execute()


async def list_research_lines(session, filters):
    query = ResearchLinesQuery(session)
    query.apply_filters(filters)
    return await query.execute()


async def list_article_production(session, program_id, year):
    query = GraduateProgramArticleProductionQuery(
        session, program_id=program_id, year=year
    )
    return await query.execute()


async def list_graduate_program_researchers(session, filters):
    query = GraduateProgramResearcherQuery(session)
    query.apply_filters(filters)
    return await query.execute()
