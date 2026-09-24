from simcc.v1.repositories import production_repo


async def list_papers_magazine(session, filters):
    return await production_repo.list_papers_magazine(session, filters)


async def list_magazine(session, filters):
    return await production_repo.list_magazine(session, filters)


async def list_recently_updated(session, filters):
    return await production_repo.list_recently_updated(session, filters)


async def list_bibliographic_production(session, filters, qualis=None):
    return await production_repo.list_bibliographic_production(
        session, filters, qualis
    )


async def list_book_chapter(session, filters):
    return await production_repo.list_book_chapter(session, filters)


async def list_book(session, filters):
    return await production_repo.list_book(session, filters)


async def list_professional_experience(session, filters):
    return await production_repo.list_professional_experience(session, filters)


async def list_patent(session, filters):
    return await production_repo.list_patent(session, filters)


async def list_participation_event(session, filters):
    return await production_repo.list_participation_event(session, filters)


async def list_brand(session, filters):
    return await production_repo.list_brand(session, filters)


async def list_researcher_report(session, filters):
    return await production_repo.list_researcher_report(session, filters)


async def list_software(session, filters):
    return await production_repo.list_software(session, filters)


async def list_guidance_production(session, filters):
    return await production_repo.list_guidance_production(session, filters)


async def list_research_projects(session, filters):
    return await production_repo.list_research_projects(session, filters)


async def list_researcher_production_events(session, filters):
    return await production_repo.list_researcher_production_events(
        session, filters
    )


async def list_researcher_scholarships(session, filters):
    return await production_repo.list_researcher_scholarships(session, filters)


async def get_graduate_program_production(session, filters):
    return await production_repo.get_graduate_program_production(
        session, filters
    )


async def list_general_production_metrics(session, filters):
    return await production_repo.list_general_production_metrics(
        session, filters
    )
