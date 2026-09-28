import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from simcc.core.dependencies import AdminAsyncSession, AsyncSession
from simcc.core.settings import Settings
from simcc.v1.services import powerBi_service

SETTINGS = Settings()
STORAGE_PATH = Path('storage/powerBI')
STORAGE_PATH.mkdir(parents=True, exist_ok=True)

router = APIRouter(tags=['Power BI'], include_in_schema=False)


@router.get('/dim_titulacao.csv')
async def dim_titulacao_xlsx(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'dim_titulacao.xlsx')
    await powerBi_service.dim_titulacao(session)
    return FileResponse(file_path, filename='dim_titulacao.xlsx')


@router.get('/fat_area_specialty.csv')
async def fat_area_specialty_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'fat_area_specialty.csv')
    await powerBi_service.fat_area_specialty(session)
    return FileResponse(file_path, filename='fat_area_specialty.csv')


@router.get('/fat_great_area.csv')
async def fat_great_area_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'fat_great_area.csv')
    await powerBi_service.fat_great_area(session)
    return FileResponse(file_path, filename='fat_great_area.csv')


@router.get('/dim_area_specialty.csv')
async def dim_area_specialty_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'dim_area_specialty.csv')
    await powerBi_service.dim_area_specialty(session)
    return FileResponse(file_path, filename='dim_area_specialty.csv')


@router.get('/dim_great_area.csv')
async def dim_great_area_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'dim_great_area.csv')
    await powerBi_service.dim_great_area(session)
    return FileResponse(file_path, filename='dim_great_area.csv')


@router.get('/fat_openalex_researcher.csv')
async def fat_openalex_researcher_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'fat_openalex_researcher.csv')
    await powerBi_service.fat_openalex_researcher(session)
    return FileResponse(file_path, filename='fat_openalex_researcher.csv')


@router.get('/researcher_area_leader.csv')
async def researcher_area_leader_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_path = os.path.join(STORAGE_PATH, 'researcher_area_leader.csv')
    await powerBi_service.researcher_area_leader(session, admin_session)
    return FileResponse(file_path, filename='researcher_area_leader.csv')


@router.get('/fat_openalex_article.csv')
async def fat_openalex_article_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'fat_openalex_article.csv')
    await powerBi_service.fat_openalex_article(session)
    return FileResponse(file_path, filename='fat_openalex_article.csv')


@router.get('/dim_area_leader.csv')
async def dim_area_leader_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'dim_area_leader.csv')
    await powerBi_service.dim_area_leader(session)
    return FileResponse(file_path, filename='dim_area_leader.csv')


@router.get('/npai.png')
async def npai_png(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'npai.png')
    await powerBi_service.npai(session)
    return FileResponse(file_path, filename='npai.png')


@router.get('/iapos.png')
async def iapos_png(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'iapos.png')
    await powerBi_service.iapos(session)
    return FileResponse(file_path, filename='iapos.png')


@router.get('/dim_city.csv')
async def dim_city_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'dim_city.csv')
    await powerBi_service.dim_city(session)
    return FileResponse(file_path, filename='dim_city.csv')


@router.get('/ufmg_researcher.csv')
async def ufmg_researcher_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'ufmg_researcher.csv')
    await powerBi_service.ufmg_researcher(session)
    return FileResponse(file_path, filename='ufmg_researcher.csv')


@router.get('/DimensaoAno.xlsx')
async def DimensaoAno_xlsx(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'DimensaoAno.xlsx')
    await powerBi_service.DimensaoAno(session)
    return FileResponse(file_path, filename='DimensaoAno.xlsx')


@router.get('/DimensaoTipoProducao.xlsx')
async def DimensaoTipoProducao_xlsx(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'DimensaoTipoProducao.xlsx')
    await powerBi_service.DimensaoTipoProducao(session)
    return FileResponse(file_path, filename='DimensaoTipoProducao.xlsx')


@router.get('/platform_image.xlsx')
async def platform_image_xlsx(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'platform_image.xlsx')
    await powerBi_service.platform_image(session)
    return FileResponse(file_path, filename='platform_image.xlsx')


@router.get('/Qualis.xlsx')
async def Qualis_xlsx(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'Qualis.xlsx')
    await powerBi_service.Qualis(session)
    return FileResponse(file_path, filename='Qualis.xlsx')


@router.get('/data.csv')
async def data_csv(session: AsyncSession):
    file_path = os.path.join(STORAGE_PATH, 'data.csv')
    await powerBi_service.data(session)
    return FileResponse(file_path, filename='data.csv')


@router.get('/cimatec_graduate_program_student.csv')
async def cimatec_graduate_program_student_csv(session: AsyncSession):
    file_name = 'cimatec_graduate_program_student.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.cimatec_graduate_program_student(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_graduate_program_acronym.csv')
async def dim_graduate_program_acronym_csv(session: AsyncSession):
    file_name = 'dim_graduate_program_acronym.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_graduate_program_acronym(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/graduate_program_researcher_year_unnest.csv')
async def graduate_program_researcher_year_unnest_csv(session: AsyncSession):
    file_name = 'graduate_program_researcher_year_unnest.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.graduate_program_researcher_year_unnest(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/graduate_program_student_year_unnest.csv')
async def graduate_program_student_year_unnest(session: AsyncSession):
    file_name = 'graduate_program_student_year_unnest.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.graduate_program_student_year_unnest(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_departament_technician.csv')
async def dim_departament_technician_csv(session: AsyncSession):
    file_name = 'dim_departament_technician.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_departament_technician(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_departament_researcher.csv')
async def dim_departament_researcher_csv(session: AsyncSession):
    file_name = 'dim_departament_researcher.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_departament_researcher(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_group_leaders.csv')
async def fat_group_leaders_csv(session: AsyncSession):
    file_name = 'fat_group_leaders.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_group_leaders(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_research_group.csv')
async def dim_research_group_csv(session: AsyncSession):
    file_name = 'dim_research_group.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_research_group(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_category_level_code.csv')
async def dim_category_level_code_csv(session: AsyncSession):
    file_name = 'dim_category_level_code.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_category_level_code(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_foment.csv')
async def fat_foment_csv(session: AsyncSession):
    file_name = 'fat_foment.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_foment(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_production_tecnical_year_novo_csv_db.csv')
async def fat_production_tecnical_year_novo_csv_db_csv(session: AsyncSession):
    file_name = 'fat_production_tecnical_year_novo_csv_db.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_production_tecnical_year_novo_csv_db(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_institution.csv')
async def dim_institution_csv(session: AsyncSession):
    file_name = 'dim_institution.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_institution(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/researcher_city.csv')
async def researcher_city_csv(session: AsyncSession):
    file_name = 'researcher_city.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.researcher_city(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_researcher.csv')
async def dim_researcher_csv(session: AsyncSession):
    origin = SETTINGS.URL
    file_name = 'dim_researcher.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_researcher(session, origin)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_simcc_bibliographic_production.csv')
async def fat_simcc_bibliographic_production_csv(session: AsyncSession):
    file_name = 'fat_simcc_bibliographic_production.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_simcc_bibliographic_production(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/production_tecnical_year.csv')
async def production_tecnical_year_csv(session: AsyncSession):
    file_name = 'production_tecnical_year.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.production_tecnical_year(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/researcher.csv')
async def researcher_csv(session: AsyncSession):
    file_name = 'researcher.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.researcher(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/article_qualis_year_institution.csv')
async def article_qualis_year_institution_csv(session: AsyncSession):
    file_name = 'article_qualis_year_institution.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.article_qualis_year_institution(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/production_researcher.csv')
async def production_researcher_csv(session: AsyncSession):
    file_name = 'production_researcher.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.production_researcher(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/article_qualis_year.csv')
async def article_qualis_year_csv(session: AsyncSession):
    file_name = 'article_qualis_year.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.article_qualis_year(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/production_year_distinct.csv')
async def production_year_distinct_csv(session: AsyncSession):
    file_name = 'production_year_distinct.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.production_year_distinct(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/production_year.csv')
async def production_year_csv(session: AsyncSession):
    file_name = 'production_year.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.production_year(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/production_coauthors_csv_db.csv')
async def production_coauthors_csv_db_csv(session: AsyncSession):
    file_name = 'production_coauthors_csv_db.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.production_coauthors_csv_db(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_researcher_ind_prod.csv')
async def fat_researcher_ind_prod_csv(session: AsyncSession):
    file_name = 'fat_researcher_ind_prod.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_researcher_ind_prod(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/graduate_program_ind_prod.csv')
async def graduate_program_ind_prod_csv(session: AsyncSession):
    file_name = 'graduate_program_ind_prod.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.graduate_program_ind_prod(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/researcher_production_novo_csv_db.csv')
async def researcher_production_novo_csv_db_csv(session: AsyncSession):
    file_name = 'researcher_production_novo_csv_db.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.researcher_production_novo_csv_db(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/article_distinct_novo_csv_db.csv')
async def article_distinct_novo_csv_db_csv(session: AsyncSession):
    file_name = 'article_distinct_novo_csv_db.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.article_distinct_novo_csv_db(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/production_distinct_novo_csv_db.csv')
async def production_distinct_novo_csv_db_csv(session: AsyncSession):
    file_name = 'production_distinct_novo_csv_db.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.production_distinct_novo_csv_db(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/cimatec_graduate_program_researcher.csv')
async def cimatec_graduate_program_researcher_csv(session: AsyncSession):
    file_name = 'cimatec_graduate_program_researcher.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.cimatec_graduate_program_researcher(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/cimatec_graduate_program.csv')
async def cimatec_graduate_program_csv(session: AsyncSession):
    file_name = 'cimatec_graduate_program.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.cimatec_graduate_program(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_departament.csv')
async def dim_departament_csv(session: AsyncSession):
    file_name = 'dim_departament.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_departament(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_research_project.csv')
async def dim_research_project_csv(session: AsyncSession):
    file_name = 'dim_research_project.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_research_project(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_research_project_foment.csv')
async def fat_research_project_foment_csv(session: AsyncSession):
    file_name = 'fat_research_project_foment.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_research_project_foment(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_bibliographic_production_terms.csv')
async def dim_bibliographic_production_terms_csv(session: AsyncSession):
    file_name = 'dim_bibliographic_production_terms.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_bibliographic_production_terms(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_tecnical_production_terms.csv')
async def dim_tecnical_production_terms_csv(session: AsyncSession):
    file_name = 'dim_tecnical_production_terms.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_tecnical_production_terms(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_logs_routine.csv')
async def dim_logs_routine_csv(session: AsyncSession):
    file_name = 'dim_logs_routine.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_logs_routine(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_event_organization.csv')
async def fat_event_organization_csv(session: AsyncSession):
    file_name = 'fat_event_organization.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_event_organization(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_participation_events.csv')
async def fat_participation_events_csv(session: AsyncSession):
    file_name = 'fat_participation_events.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_participation_events(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/materialized_vision.csv')
async def materialized_vision_csv(session: AsyncSession):
    file_name = 'materialized_vision.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.materialized_vision(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_article_keyword.csv')
async def dim_article_keyword_csv(session: AsyncSession):
    file_name = 'dim_article_keyword.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_article_keyword(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_article_keyword_.csv')
async def fat_article_keyword_csv(session: AsyncSession):
    file_name = 'fat_article_keyword_.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_article_keyword_(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_article_co_authorship.csv')
async def fat_article_co_authorship_csv(session: AsyncSession):
    file_name = 'fat_article_co_authorship.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_article_co_authorship(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_keywords_cooccurrences.csv')
async def fat_keywords_cooccurrences(session: AsyncSession):
    file_name = 'fat_keywords_cooccurrences.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_keywords_cooccurrences(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_co_authorship.csv')
async def fat_co_authorship_csv(session: AsyncSession):
    file_name = 'fat_co_authorship.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_co_authorship(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/guidance.csv')
async def guidance_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'guidance.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.guidance(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/supervisor.csv')
async def supervisor_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'supervisor.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.supervisor(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/guidance_per_year.csv')
async def guidance_per_year_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'guidance_per_year.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.guidance_per_year(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/in_progress_per_year.csv')
async def in_progress_per_year_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'in_progress_per_year.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.in_progress_per_year(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_tags.csv')
async def dim_tags_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'dim_tags.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_tags_csv(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_tags.csv')
async def fat_tags_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'fat_tags.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_tags_csv(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/EtapaOrientacao.xlsx')
async def EtapaOrientacao(session: AsyncSession):
    powerBi_service._ensure_static_file('EtapaOrientacao.xlsx')
    file_name = 'EtapaOrientacao.xlsx'
    file_path = os.path.join(STORAGE_PATH, file_name)
    return FileResponse(file_path, filename=file_name)


@router.get('/ind_guidance_ori.csv')
async def ind_guidance_ori_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'ind_guidance_ori.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.ind_guidance_ori(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/ind_guidance_distori.csv')
async def ind_guidance_distori_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'ind_guidance_distori.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.ind_guidance_distori(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/ind_guidance_coaut.csv')
async def ind_guidance_coaut_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'ind_guidance_coaut.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.ind_guidance_coaut(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_sdg.csv')
async def dim_sdg_csv(session: AsyncSession):
    file_name = 'dim_sdg.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_sdg(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_sdg_articles.csv')
async def fat_sdg_articles_csv(session: AsyncSession):
    file_name = 'fat_sdg_articles.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_sdg_articles(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_sdg_alignment_researcher.csv')
async def fat_sdg_alignment_researcher_csv(session: AsyncSession):
    file_name = 'fat_sdg_alignment_researcher.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_sdg_alignment_researcher(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_guidance_history.csv')
async def fat_guidance_history_csv(
    session: AsyncSession, admin_session: AdminAsyncSession
):
    file_name = 'fat_guidance_history.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_guidance_history(session, admin_session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_territorio_identidade.csv')
async def dim_territorio_identidade_csv(session: AsyncSession):
    file_name = 'dim_territorio_identidade.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_territorio_identidade(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_log_category.csv')
async def dim_log_category_csv(session: AsyncSession):
    file_name = 'dim_log_category.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_log_category(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/dim_log_event.csv')
async def dim_log_event_csv(session: AsyncSession):
    file_name = 'dim_log_event.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.dim_log_event(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_logs.csv')
async def fat_logs_csv(session: AsyncSession):
    file_name = 'fat_logs.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_logs(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_logs_http.csv')
async def fat_logs_http_csv(session: AsyncSession):
    file_name = 'fat_logs_http.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_logs_http(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_logs_database.csv')
async def fat_logs_database_csv(session: AsyncSession):
    file_name = 'fat_logs_database.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_logs_database(session)
    return FileResponse(file_path, filename=file_name)


@router.get('/fat_logs_routine.csv')
async def _fat_logs_routine_csv(session: AsyncSession):
    file_name = 'fat_logs_routine.csv'
    file_path = os.path.join(STORAGE_PATH, file_name)
    await powerBi_service.fat_logs_routine(session)
    return FileResponse(file_path, filename=file_name)
