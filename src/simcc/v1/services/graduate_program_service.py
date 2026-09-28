from simcc.v1.repositories import graduate_program_repo


async def list_graduate_programs(session, filters):
    return await graduate_program_repo.list_graduate_programs(session, filters)


async def list_research_lines(session, filters):
    return await graduate_program_repo.list_research_lines(session, filters)


async def list_article_production(session, program_id, year):
    return await graduate_program_repo.list_article_production(
        session, program_id, year
    )


async def list_graduate_program_researchers(session, filters):
    return await graduate_program_repo.list_graduate_program_researchers(
        session, filters
    )
