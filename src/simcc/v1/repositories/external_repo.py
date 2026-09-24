from simcc.v1.queries import external_query


async def list_article_production(
    session, program_id=None, dep_id=None, year=2020
):
    try:
        query = external_query.ResearcherArticleProductionQuery(
            session, program_id, dep_id, year
        )
        return await query.execute()
    except Exception:
        return []


async def get_departament(session, dep_id=None):
    try:
        query = external_query.DepartmentSearchQuery(session, dep_id)
        return await query.execute()
    except Exception:
        return []


async def get_docentes(session, filters):
    try:
        query = external_query.DocenteSearchQuery(session)
        query.apply_filters(filters)
        return await query.execute()
    except Exception:
        return []


async def get_researcher_data(session, cpf=None, name=None):
    try:
        query = external_query.ResearcherDataQuery(session, cpf, name)
        return await query.execute()
    except Exception:
        return []


async def get_technician(session):
    try:
        query = external_query.TechnicianQuery(session)
        return await query.execute()
    except Exception:
        return []


async def list_words(session, term: str, stopwords: list[str]):
    try:
        query = external_query.WordFrequencyQuery(session, term, stopwords)
        return await query.execute()
    except Exception:
        return []


async def get_departament_rt(session):
    # Schema legado ufmg descontinuado - retorno fixo compatível
    return {'teachers': [], 'technician': []}


async def post_congregation(session, congregation: list):
    # Schema legado ufmg descontinuado - no-op
    return None
