from simcc.v1.queries import powerBi_query


async def get_fat_area_specialty(session):
    query = powerBi_query.FatAreaSpecialtyQuery(session)
    return await query.execute()


async def get_fat_great_area(session):
    query = powerBi_query.FatGreatAreaQuery(session)
    return await query.execute()


async def get_dim_area_specialty(session):
    query = powerBi_query.DimAreaSpecialtyQuery(session)
    return await query.execute()


async def get_dim_great_area(session):
    query = powerBi_query.DimGreatAreaQuery(session)
    return await query.execute()


async def get_fat_openalex_researcher(session):
    query = powerBi_query.FatOpenalexResearcherQuery(session)
    return await query.execute()


async def get_researcher_area_leader(admin_session):
    query = powerBi_query.ResearcherAreaLeaderQuery(admin_session)
    return await query.execute()


async def get_researcher_area_leader_researcher(session):
    query = powerBi_query.ResearcherAreaLeaderResearcherQuery(session)
    return await query.execute()


async def get_fat_openalex_article(session):
    query = powerBi_query.FatOpenalexArticleQuery(session)
    return await query.execute()


async def get_dim_area_leader(session):
    query = powerBi_query.DimAreaLeaderQuery(session)
    return await query.execute()


async def get_dim_city(session):
    query = powerBi_query.DimCityQuery(session)
    return await query.execute()


async def get_ufmg_researcher(session):
    # Schema legado ufmg descontinuado - retorno fixo compatível
    return []


async def get_dim_departament(session):
    # Schema legado ufmg descontinuado - retorno fixo compatível
    return []


async def get_cimatec_graduate_program_student(session):
    query = powerBi_query.CimatecGraduateProgramStudentQuery(session)
    return await query.execute()


async def get_graduate_program_student_year_unnest(session):
    query = powerBi_query.GraduateProgramStudentYearUnnestQuery(session)
    return await query.execute()


async def get_dim_graduate_program_acronym(session):
    query = powerBi_query.DimGraduateProgramAcronymQuery(session)
    return await query.execute()


async def get_graduate_program_researcher_year_unnest(session):
    query = powerBi_query.GraduateProgramResearcherYearUnnestQuery(session)
    return await query.execute()


async def get_dim_departament_technician(session):
    # Schema legado ufmg descontinuado - retorno fixo compatível
    return []


async def get_dim_departament_researcher(session):
    # Schema legado ufmg descontinuado - retorno fixo compatível
    return []


async def get_fat_group_leaders(session):
    query = powerBi_query.FatGroupLeadersQuery(session)
    return await query.execute()


async def get_dim_research_group(session):
    query = powerBi_query.DimResearchGroupQuery(session)
    return await query.execute()


async def get_dim_category_level_code(session):
    query = powerBi_query.DimCategoryLevelCodeQuery(session)
    return await query.execute()


async def get_fat_foment(session):
    query = powerBi_query.FatFomentQuery(session)
    return await query.execute()


async def get_fat_production_tecnical_year_novo_csv_db(session):
    query = powerBi_query.FatProductionTecnicalYearNovoCsvDbQuery(session)
    return await query.execute()


async def get_dim_institution(session):
    query = powerBi_query.DimInstitutionQuery(session)
    return await query.execute()


async def get_researcher_city(session):
    query = powerBi_query.ResearcherCityQuery(session)
    return await query.execute()


async def get_dim_researcher(session, origin):
    query = powerBi_query.DimResearcherQuery(session)
    query.params = {'origin': origin}
    return await query.execute()


async def get_dim_researcher_words(session, stopwords):
    query = powerBi_query.DimResearcherWordsQuery(session)
    query.params = {'stopwords': stopwords}
    return await query.execute()


async def get_fat_simcc_bibliographic_production(session):
    query = powerBi_query.FatSimccBibliographicProductionQuery(session)
    return await query.execute()


async def get_production_tecnical_year(session):
    query = powerBi_query.ProductionTecnicalYearQuery(session)
    return await query.execute()


async def get_researcher(session):
    query = powerBi_query.ResearcherQuery(session)
    return await query.execute()


async def get_article_qualis_year_institution(session):
    query = powerBi_query.ArticleQualisYearInstitutionQuery(session)
    return await query.execute()


async def get_production_researcher(session):
    query = powerBi_query.ProductionResearcherQuery(session)
    return await query.execute()


async def get_article_qualis_year(session):
    query = powerBi_query.ArticleQualisYearQuery(session)
    return await query.execute()


async def get_production_year_distinct(session):
    query = powerBi_query.ProductionYearDistinctQuery(session)
    return await query.execute()


async def get_production_year(session):
    query = powerBi_query.ProductionYearQuery(session)
    return await query.execute()


async def get_production_coauthors_csv_db(session):
    query = powerBi_query.ProductionCoauthorsCsvDbQuery(session)
    return await query.execute()


async def get_fat_researcher_ind_prod(session):
    query = powerBi_query.FatResearcherIndProdQuery(session)
    return await query.execute()


async def get_graduate_program_ind_prod(session):
    query = powerBi_query.GraduateProgramIndProdQuery(session)
    return await query.execute()


async def get_researcher_production_novo_csv_db(session):
    query = powerBi_query.ResearcherProductionNovoCsvDbQuery(session)
    return await query.execute()


async def get_article_distinct_novo_csv_db(session):
    query = powerBi_query.ArticleDistinctNovoCsvDbQuery(session)
    return await query.execute()


async def get_production_distinct_novo_csv_db(session):
    query = powerBi_query.ProductionDistinctNovoCsvDbQuery(session)
    return await query.execute()


async def get_cimatec_graduate_program_researcher(session):
    query = powerBi_query.CimatecGraduateProgramResearcherQuery(session)
    return await query.execute()


async def get_cimatec_graduate_program(session):
    query = powerBi_query.CimatecGraduateProgramQuery(session)
    return await query.execute()


async def get_dim_research_project(session):
    query = powerBi_query.DimResearchProjectQuery(session)
    return await query.execute()


async def get_fat_research_project_foment(session):
    query = powerBi_query.FatResearchProjectFomentQuery(session)
    return await query.execute()


async def get_dim_bibliographic_production_terms(session, stopwords):
    query = powerBi_query.DimBibliographicProductionTermsQuery(session)
    query.params = {'stopwords': stopwords}
    return await query.execute()


async def get_dim_tecnical_production_terms(session, stopwords):
    query = powerBi_query.DimTecnicalProductionTermsQuery(session)
    query.params = {'stopwords': stopwords}
    return await query.execute()


async def get_dim_logs_routine(session):
    query = powerBi_query.DimLogsRoutineQuery(session)
    return await query.execute()


async def get_fat_logs_routine(session):
    query = powerBi_query.FatLogsRoutineQuery(session)
    return await query.execute()


async def get_fat_event_organization(session):
    query = powerBi_query.FatEventOrganizationQuery(session)
    return await query.execute()


async def get_fat_participation_events(session):
    query = powerBi_query.FatParticipationEventsQuery(session)
    return await query.execute()


async def get_materialized_vision(session):
    query = powerBi_query.MaterializedVisionQuery(session)
    return await query.execute()


async def get_dim_article_keyword(session, stopwords):
    query = powerBi_query.DimArticleKeywordQuery(session)
    query.params = {'stopwords': stopwords}
    return await query.execute()


async def get_fat_article_keyword_(session, stopwords):
    query = powerBi_query.FatArticleKeywordUnderscoreQuery(session)
    query.params = {'stopwords': stopwords}
    return await query.execute()


async def get_fat_article_co_authorship(session):
    query = powerBi_query.FatArticleCoAuthorshipQuery(session)
    return await query.execute()


async def get_fat_keywords_cooccurrences(session, stopwords):
    query = powerBi_query.FatKeywordsCooccurrencesQuery(session)
    query.params = {'stopwords': stopwords}
    return await query.execute()


async def get_fat_co_authorship(session):
    query = powerBi_query.FatCoAuthorshipQuery(session)
    return await query.execute()


async def get_guidance(admin_session):
    try:
        query = powerBi_query.GuidanceQuery(admin_session)
        return await query.execute()
    except Exception:
        return []


async def get_guidance_researcher(session):
    try:
        query = powerBi_query.GuidanceResearcherQuery(session)
        return await query.execute()
    except Exception:
        return []


async def get_dim_tags(admin_session):
    try:
        query = powerBi_query.DimTagsQuery(admin_session)
        return await query.execute()
    except Exception:
        return []


async def get_fat_tags(admin_session):
    try:
        query = powerBi_query.FatTagsQuery(admin_session)
        return await query.execute()
    except Exception:
        return []


async def get_dim_sdg(session):
    query = powerBi_query.DimSdgQuery(session)
    return await query.execute()


async def get_fat_sdg_articles(session):
    query = powerBi_query.FatSdgArticlesQuery(session)
    return await query.execute()


async def get_fat_sdg_alignment_researcher(session):
    query = powerBi_query.FatSdgAlignmentResearcherQuery(session)
    return await query.execute()


async def get_ind_guidance_ori(admin_session):
    try:
        query = powerBi_query.IndGuidanceOriQuery(admin_session)
        return await query.execute()
    except Exception:
        return []


async def get_ind_guidance_coaut_prog(admin_session):
    try:
        query = powerBi_query.IndGuidanceCoautProgQuery(admin_session)
        return await query.execute()
    except Exception:
        return []


async def get_ind_guidance_coaut_prod(session):
    try:
        query = powerBi_query.IndGuidanceCoautProdQuery(session)
        return await query.execute()
    except Exception:
        return []


async def get_ind_guidance_distori(admin_session):
    try:
        query = powerBi_query.IndGuidanceDistoriQuery(admin_session)
        return await query.execute()
    except Exception:
        return []


async def get_fat_guidance_history(admin_session):
    try:
        query = powerBi_query.FatGuidanceHistoryQuery(admin_session)
        return await query.execute()
    except Exception:
        return []
