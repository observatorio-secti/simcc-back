import json
import os
import shutil
from datetime import date, datetime

import polars as pl

from simcc.core.settings import Settings
from simcc.v1.repositories import powerBi_repo

PATH = 'storage/powerBI'

STATIC_HEADERS = {
    'researcher_area_leader.csv': '"",researcher_id,area_leader,focal_point\n',
    'guidance.csv': (
        '"","id","student_lattes_id","supervisor_lattes_id",'
        '"co_supervisor_lattes_id","graduate_program_id","start_date",'
        '"planned_date_project","done_date_project","planned_date_qualification",'
        '"done_date_qualification","planned_date_conclusion","done_date_conclusion",'
        '"student_name","supervisor_name","co_name","student_researcher_id",'
        '"supervisor_researcher_id","co_supervisor_researcher_id","program_type",'
        '"peding_days","peding","type","days_offset"\n'
    ),
    'supervisor.csv': '"",supervisor_researcher_id,year,count\n',
    'guidance_per_year.csv': (
        '"","id","graduate_program_id","student_name","student_researcher_id",'
        '"supervisor_name","supervisor_researcher_id","co_name",'
        '"co_supervisor_researcher_id","type","status_","year","in_progress"\n'
    ),
    'in_progress_per_year.csv': (
        'in_progress,year,supervisor_name,supervisor_researcher_id,graduate_program_id,count\n'
    ),
    'dim_tags.csv': '"","id","name","color_code"\n',
    'fat_tags.csv': '"","guidance_tracking_id","tag_id"\n',
    'ind_guidance_ori.csv': (
        '"","graduate_program_id","year","masters_defenses","doctorate_defenses",'
        '"permanent_researchers","ind_ori"\n'
    ),
    'ind_guidance_distori.csv': (
        '"","graduate_program_id","year","concluding_researchers","permanent_researchers",'
        '"ind_dist_ori"\n'
    ),
    'ind_guidance_coaut.csv': (
        '"graduate_program_id","year","IndProdArtCoAut","IndProdLivCoAut","IndProdCapCoAut"\n'
    ),
    'fat_guidance_history.csv': '"","student_name","student_id","supervisor_id","year","type"\n',
}


def _ensure_static_file(filename):
    dest_path = os.path.join(PATH, filename)
    if not os.path.exists(dest_path):
        src_path = os.path.join('storage/powerBI', filename)
        if os.path.exists(src_path):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy(src_path, dest_path)
        elif filename in STATIC_HEADERS:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(STATIC_HEADERS[filename])


def parse_date(val):
    if val is None or val == 'None' or val == '':
        return None
    if isinstance(val, (datetime, date)):
        return val
    try:
        return datetime.fromisoformat(str(val)).date()
    except Exception:
        try:
            return datetime.strptime(str(val).split()[0], '%Y-%m-%d').date()
        except Exception:
            return None


async def dim_titulacao(session):
    print('Dimensão da Tabela Titulação!')
    _ensure_static_file('dim_titulacao.xlsx')


async def fat_area_specialty(session):
    data = await powerBi_repo.get_fat_area_specialty(session)
    df_schema = {
        'area_specialty_id': pl.Utf8,
        'researcher_id': pl.Utf8,
        'area_specialty': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    csv_path = os.path.join(PATH, 'fat_area_specialty.csv')
    df.write_csv(csv_path)


async def fat_great_area(session):
    data = await powerBi_repo.get_fat_great_area(session)
    df_schema = {
        'great_area_id': pl.Utf8,
        'researcher_id': pl.Utf8,
        'name': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_great_area.csv'))


async def dim_area_specialty(session):
    data = await powerBi_repo.get_dim_area_specialty(session)
    df_schema = {
        'id': pl.Utf8,
        'name': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_area_specialty.csv'))


async def dim_great_area(session):
    data = await powerBi_repo.get_dim_great_area(session)
    df_schema = {
        'id': pl.Utf8,
        'name': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_great_area.csv'))


async def fat_openalex_researcher(session):
    data = await powerBi_repo.get_fat_openalex_researcher(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'h_index': pl.Utf8,
        'relevance_score': pl.Utf8,
        'works_count': pl.Utf8,
        'cited_by_count': pl.Utf8,
        'i10_index': pl.Utf8,
        'scopus': pl.Utf8,
        'orcid': pl.Utf8,
        'openalex': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_openalex_researcher.csv'))


async def researcher_area_leader(session=None, admin_session=None):
    _ensure_static_file('researcher_area_leader.csv')


async def fat_openalex_article(session):
    data = await powerBi_repo.get_fat_openalex_article(session)
    df_schema = {
        'article_id': pl.Utf8,
        'article_institution': pl.Utf8,
        'issn': pl.Utf8,
        'authors_institution': pl.Utf8,
        'abstract': pl.Utf8,
        'authors': pl.Utf8,
        'language': pl.Utf8,
        'citations_count': pl.Utf8,
        'pdf': pl.Utf8,
        'landing_page_url': pl.Utf8,
        'keywords': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_openalex_article.csv'))


async def dim_area_leader(session):
    data = await powerBi_repo.get_dim_area_leader(session)
    df_schema = {
        'area_leader': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_area_leader.csv'))


async def npai(session):
    print('Imagem NPAI!')
    _ensure_static_file('npai.png')


async def iapos(session):
    print('Imagem NPAI!')
    _ensure_static_file('iapos.png')


async def dim_city(session):
    data = await powerBi_repo.get_dim_city(session)
    df_schema = {
        'city_id': pl.Utf8,
        'name': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_city.csv'))


async def ufmg_researcher(session):
    data = await powerBi_repo.get_ufmg_researcher(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'full_name': pl.Utf8,
        'gender': pl.Utf8,
        'status_code': pl.Utf8,
        'work_regime': pl.Utf8,
        'job_class': pl.Utf8,
        'job_title': pl.Utf8,
        'job_rank': pl.Utf8,
        'job_reference_code': pl.Utf8,
        'academic_degree': pl.Utf8,
        'organization_entry_date': pl.Utf8,
        'last_promotion_date': pl.Utf8,
        'employment_status_description': pl.Utf8,
        'department_name': pl.Utf8,
        'career_category': pl.Utf8,
        'academic_unit': pl.Utf8,
        'unit_code': pl.Utf8,
        'function_code': pl.Utf8,
        'position_code': pl.Utf8,
        'leadership_start_date': pl.Utf8,
        'leadership_end_date': pl.Utf8,
        'current_function_name': pl.Utf8,
        'function_location': pl.Utf8,
        'registration_number': pl.Utf8,
        'ufmg_registration_number': pl.Utf8,
        'semester_reference': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.fill_null('0')
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'ufmg_researcher.csv'))


async def DimensaoAno(session):
    print('Dimensão da Tabela Ano!')
    _ensure_static_file('DimensaoAno.xlsx')


async def DimensaoTipoProducao(session):
    print('Dimensão da Tabela TipoProducao!')
    _ensure_static_file('DimensaoTipoProducao.xlsx')


async def platform_image(session):
    print('Dimensão da Tabela Platform Image!')
    _ensure_static_file('platform_image.xlsx')


async def Qualis(session):
    print('Dimensão da Tabela Qualis!')
    _ensure_static_file('Qualis.xlsx')


async def data(session):
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d %H:%M:%S.%f')
    df = pl.DataFrame({'data': [date_str]})
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'data.csv'))
    return date_str


async def cimatec_graduate_program_student(session):
    data = await powerBi_repo.get_cimatec_graduate_program_student(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'graduate_program_id': pl.Utf8,
        'year': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'cimatec_graduate_program_student.csv'))


async def dim_graduate_program_acronym(session):
    data = await powerBi_repo.get_dim_graduate_program_acronym(session)
    df_schema = {
        'graduate_program_id': pl.Utf8,
        'acronym': pl.Utf8,
        'name': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_graduate_program_acronym.csv'))


async def graduate_program_researcher_year_unnest(session):
    data = await powerBi_repo.get_graduate_program_researcher_year_unnest(
        session
    )
    df_schema = {
        'graduate_program_id': pl.Utf8,
        'researcher_id': pl.Utf8,
        'year': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(
        os.path.join(PATH, 'graduate_program_researcher_year_unnest.csv')
    )


async def graduate_program_student_year_unnest(session):
    data = await powerBi_repo.get_graduate_program_student_year_unnest(session)
    df_schema = {
        'graduate_program_id': pl.Utf8,
        'researcher_id': pl.Utf8,
        'year': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(
        os.path.join(PATH, 'graduate_program_student_year_unnest.csv')
    )


async def dim_departament_technician(session):
    data = await powerBi_repo.get_dim_departament_technician(session)
    df_schema = {
        'dep_id': pl.Utf8,
        'technician_id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.fill_null('0')
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_departament_technician.csv'))


async def dim_departament_researcher(session):
    data = await powerBi_repo.get_dim_departament_researcher(session)
    df_schema = {
        'dep_id': pl.Utf8,
        'researcher_id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.fill_null('0')
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_departament_researcher.csv'))


async def fat_group_leaders(session):
    data = await powerBi_repo.get_fat_group_leaders(session)
    df_schema = {
        'id': pl.Utf8,
        'name': pl.Utf8,
        'institution': pl.Utf8,
        'first_leader': pl.Utf8,
        'first_leader_id': pl.Utf8,
        'second_leader': pl.Utf8,
        'second_leader_id': pl.Utf8,
        'AREA': pl.Utf8,
        'census': pl.Utf8,
        'start_of_collection': pl.Utf8,
        'end_of_collection': pl.Utf8,
        'group_identifier': pl.Utf8,
        'YEAR': pl.Utf8,
        'institution_name': pl.Utf8,
        'category': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_group_leaders.csv'))


async def dim_research_group(session):
    data = await powerBi_repo.get_dim_research_group(session)
    df_schema = {
        'group_id': pl.Utf8,
        'group_name': pl.Utf8,
        'area': pl.Utf8,
        'institution_id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_research_group.csv'))


async def dim_category_level_code(session):
    data = await powerBi_repo.get_dim_category_level_code(session)
    df_schema = {
        'category_level_code': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_category_level_code.csv'))


async def fat_foment(session):
    data = await powerBi_repo.get_fat_foment(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'institution_id': pl.Utf8,
        'modality_code': pl.Utf8,
        'modality_name': pl.Utf8,
        'category_level_code': pl.Utf8,
        'funding_program_name': pl.Utf8,
        'aid_quantity': pl.Utf8,
        'scholarship_quantity': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_foment.csv'))


async def fat_production_tecnical_year_novo_csv_db(session):
    data = await powerBi_repo.get_fat_production_tecnical_year_novo_csv_db(
        session
    )
    df_schema = {
        'title': pl.Utf8,
        'year': pl.Utf8,
        'type': pl.Utf8,
        'researcher_id': pl.Utf8,
        'city_id': pl.Utf8,
        'institution_id': pl.Utf8,
        'sanitized_title': pl.Utf8,
        'id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(
        os.path.join(PATH, 'fat_production_tecnical_year_novo_csv_db.csv')
    )


async def dim_institution(session):
    data = await powerBi_repo.get_dim_institution(session)
    df_schema = {
        'institution_id': pl.Utf8,
        'name': pl.Utf8,
        'acronym': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_institution.csv'))


async def researcher_city(session):
    data = await powerBi_repo.get_researcher_city(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'city': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'researcher_city.csv'))


async def dim_researcher(session, origin):
    data = await powerBi_repo.get_dim_researcher(session, origin)
    df_schema = {
        'researcher': pl.Utf8,
        'researcher_id': pl.Utf8,
        'last_update': pl.Utf8,
        'graduation': pl.Utf8,
        'institution_id': pl.Utf8,
        'docente': pl.Utf8,
        'abstract': pl.Utf8,
        'image': pl.Utf8,
        'orcid': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)

    import nltk

    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')
    stopwords += nltk.corpus.stopwords.words('portuguese')

    words_data = await powerBi_repo.get_dim_researcher_words(
        session, stopwords
    )
    df_words = pl.DataFrame(
        words_data,
        schema={
            'researcher_id': pl.Utf8,
            'list_of_words': pl.Utf8,
        },
    )

    df = df.join(df_words, on='researcher_id', how='left')
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_researcher.csv'))


async def fat_simcc_bibliographic_production(session):
    data = await powerBi_repo.get_fat_simcc_bibliographic_production(session)
    df_schema = {
        'title': pl.Utf8,
        'tipo': pl.Utf8,
        'researcher_id': pl.Utf8,
        'year': pl.Utf8,
        'institution_id': pl.Utf8,
        'qualis': pl.Utf8,
        'periodical_magazine_name': pl.Utf8,
        'jcr': pl.Utf8,
        'jcr_link': pl.Utf8,
        'city_id': pl.Utf8,
        'bibliographic_production_id': pl.Utf8,
        'sanitized_title': pl.Utf8,
        'id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_simcc_bibliographic_production.csv'))


async def production_tecnical_year(session):
    data = await powerBi_repo.get_production_tecnical_year(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'title': pl.Utf8,
        'year': pl.Utf8,
        'type': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'production_tecnical_year.csv'))


async def researcher(session):
    data = await powerBi_repo.get_researcher(session)
    df_schema = {
        'researcher': pl.Utf8,
        'researcher_id': pl.Utf8,
        'last_update': pl.Utf8,
        'graduation': pl.Utf8,
        'lattes_id': pl.Utf8,
        'area_leader': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'researcher.csv'))


async def article_qualis_year_institution(session):
    data = await powerBi_repo.get_article_qualis_year_institution(session)
    df_schema = {
        'title': pl.Utf8,
        'qualis': pl.Utf8,
        'jcr': pl.Utf8,
        'year': pl.Utf8,
        'institution': pl.Utf8,
        'city': pl.Utf8,
        'jcr_link': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'article_qualis_year_institution.csv'))


async def production_researcher(session):
    data = await powerBi_repo.get_production_researcher(session)
    df_schema = {
        'researcher': pl.Utf8,
        'researcher_id': pl.Utf8,
        'articles': pl.Utf8,
        'book_chapters': pl.Utf8,
        'book': pl.Utf8,
        'work_in_event': pl.Utf8,
        'great_area': pl.Utf8,
        'area_specialty': pl.Utf8,
        'graduation': pl.Utf8,
        'city': pl.Utf8,
    }
    df_researcher = pl.DataFrame(data, schema=df_schema)

    _ensure_static_file('dim_territorio_identidade.csv')
    path_dim = os.path.join(PATH, 'dim_territorio_identidade.csv')
    df_territorio = pl.read_csv(path_dim)

    from unidecode import unidecode

    def normalize_str(s):
        if s is None:
            return ''
        return unidecode(str(s)).lower().strip()

    df_researcher = df_researcher.with_columns(
        pl
        .col('city')
        .map_elements(normalize_str, return_dtype=pl.Utf8)
        .alias('city_norm')
    )
    df_territorio = df_territorio.with_columns(
        pl
        .col('Municipio')
        .map_elements(normalize_str, return_dtype=pl.Utf8)
        .alias('Municipio_norm')
    )

    df_final = df_researcher.join(
        df_territorio.select(['Territorio_ID', 'Municipio_norm']),
        left_on='city_norm',
        right_on='Municipio_norm',
        how='left',
    )

    df_final = df_final.with_columns(
        pl.col('Territorio_ID').fill_null(0).cast(pl.Int64).alias('t_id')
    )

    df_final = df_final.drop(['city_norm', 'Territorio_ID'])
    df_final.write_csv(os.path.join(PATH, 'production_researcher.csv'))


async def article_qualis_year(session):
    data = await powerBi_repo.get_article_qualis_year(session)
    df_schema = {
        'title': pl.Utf8,
        'qualis': pl.Utf8,
        'year': pl.Utf8,
        'researcher_id': pl.Utf8,
        'researcher': pl.Utf8,
        'institution': pl.Utf8,
        'city': pl.Utf8,
        'name_magazine': pl.Utf8,
        'issn': pl.Utf8,
        'jcr': pl.Utf8,
        'jcr_link': pl.Utf8,
        'type': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'article_qualis_year.csv'))


async def production_year_distinct(session):
    data = await powerBi_repo.get_production_year_distinct(session)
    df_schema = {
        'year': pl.Utf8,
        'title': pl.Utf8,
        'tipo': pl.Utf8,
        'institution': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'production_year_distinct.csv'))


async def production_year(session):
    data = await powerBi_repo.get_production_year(session)
    df_schema = {
        'title': pl.Utf8,
        'tipo': pl.Utf8,
        'researcher_id': pl.Utf8,
        'year': pl.Utf8,
        'institution': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'production_year.csv'))


async def production_coauthors_csv_db(session):
    data = await powerBi_repo.get_production_coauthors_csv_db(session)
    df_schema = {
        'qtd': pl.Utf8,
        'doi': pl.Utf8,
        'title': pl.Utf8,
        'qualis': pl.Utf8,
        'year': pl.Utf8,
        'graduate_program_id': pl.Utf8,
        'year_pos': pl.Utf8,
        'type': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'production_coauthors_csv_db.csv'))


async def fat_researcher_ind_prod(session):
    data = await powerBi_repo.get_fat_researcher_ind_prod(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'year': pl.Utf8,
        'ind_prod_article': pl.Utf8,
        'ind_prod_book': pl.Utf8,
        'ind_prod_book_chapter': pl.Utf8,
        'ind_prod_granted_patent': pl.Utf8,
        'ind_prod_not_granted_patent': pl.Utf8,
        'ind_prod_software': pl.Utf8,
        'ind_prod_report': pl.Utf8,
        'ind_prod_guidance': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df.write_csv(
        os.path.join(PATH, 'fat_researcher_ind_prod.csv'), separator=';'
    )


async def graduate_program_ind_prod(session):
    data = await powerBi_repo.get_graduate_program_ind_prod(session)
    df_schema = {
        'graduate_program_id': pl.Utf8,
        'year': pl.Utf8,
        'ind_prod_article': pl.Utf8,
        'ind_prod_book': pl.Utf8,
        'ind_prod_book_chapter': pl.Utf8,
        'ind_prod_granted_patent': pl.Utf8,
        'ind_prod_not_granted_patent': pl.Utf8,
        'ind_prod_software': pl.Utf8,
        'ind_prod_report': pl.Utf8,
        'ind_prod_guidance': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df.write_csv(
        os.path.join(PATH, 'graduate_program_ind_prod.csv'), separator=';'
    )


async def researcher_production_novo_csv_db(session):
    data = await powerBi_repo.get_researcher_production_novo_csv_db(session)
    df_schema = {
        'title': pl.Utf8,
        'qualis': pl.Utf8,
        'year': pl.Utf8,
        'researcher_id': pl.Utf8,
        'researcher': pl.Utf8,
        'name_magazine': pl.Utf8,
        'issn': pl.Utf8,
        'jcr': pl.Utf8,
        'jcr_link': pl.Utf8,
        'type': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'researcher_production_novo_csv_db.csv'))


async def article_distinct_novo_csv_db(session):
    data = await powerBi_repo.get_article_distinct_novo_csv_db(session)
    df_schema = {
        'title': pl.Utf8,
        'qualis': pl.Utf8,
        'jcr': pl.Utf8,
        'year': pl.Utf8,
        'graduate_program_id': pl.Utf8,
        'year_pos': pl.Utf8,
        'type': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'article_distinct_novo_csv_db.csv'))


async def production_distinct_novo_csv_db(session):
    data = await powerBi_repo.get_production_distinct_novo_csv_db(session)
    df_schema = {
        'title': pl.Utf8,
        'qualis': pl.Utf8,
        'jcr': pl.Utf8,
        'year': pl.Utf8,
        'graduate_program_id': pl.Utf8,
        'year_pos': pl.Utf8,
        'type': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'production_distinct_novo_csv_db.csv'))


async def cimatec_graduate_program_researcher(session):
    data = await powerBi_repo.get_cimatec_graduate_program_researcher(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'graduate_program_id': pl.Utf8,
        'year': pl.Utf8,
        'type_': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'cimatec_graduate_program_researcher.csv'))


async def cimatec_graduate_program(session):
    data = await powerBi_repo.get_cimatec_graduate_program(session)
    df_schema = {
        'graduate_program_id': pl.Utf8,
        'code': pl.Utf8,
        'name': pl.Utf8,
        'area': pl.Utf8,
        'modality': pl.Utf8,
        'type': pl.Utf8,
        'rating': pl.Utf8,
        'institution_id': pl.Utf8,
        'institution': pl.Utf8,
        'city': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'cimatec_graduate_program.csv'))


async def dim_departament(session):
    data = await powerBi_repo.get_dim_departament(session)
    df_schema = {
        'dep_id': pl.Utf8,
        'dep_nom': pl.Utf8,
        'institution': pl.Utf8,
        'institution_id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.fill_null('0')
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_departament.csv'))


def _process_and_save_chunk(
    data, df_schema, file_path, is_first_chunk, row_index_offset
):
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_columns(
        pl
        .col('start_year')
        .cast(pl.Int64, strict=False)
        .fill_null(0)
        .cast(pl.Utf8),
        pl
        .col('end_year')
        .cast(pl.Int64, strict=False)
        .fill_null(0)
        .cast(pl.Utf8),
    )
    df = df.with_row_index(name='', offset=row_index_offset)

    mode = 'w' if is_first_chunk else 'a'
    with open(file_path, mode=mode, encoding='utf-8') as f:
        df.write_csv(f, include_header=is_first_chunk)


async def dim_research_project(session):

    data = await powerBi_repo.get_dim_research_project(session)

    df_schema = {
        'id': pl.Utf8,
        'researcher_id': pl.Utf8,
        'start_year': pl.Utf8,
        'end_year': pl.Utf8,
        'agency_code': pl.Utf8,
        'agency_name': pl.Utf8,
        'project_name': pl.Utf8,
        'status': pl.Utf8,
        'nature': pl.Utf8,
        'number_undergraduates': pl.Utf8,
        'description': pl.Utf8,
        'number_specialists': pl.Utf8,
        'number_academic_masters': pl.Utf8,
        'number_phd': pl.Utf8,
    }

    df = pl.DataFrame(data, schema=df_schema)

    df = df.with_columns(
        pl
        .col('start_year')
        .cast(pl.Int64, strict=False)
        .fill_null(0)
        .cast(pl.Utf8),
        pl
        .col('end_year')
        .cast(pl.Int64, strict=False)
        .fill_null(0)
        .cast(pl.Utf8),
    )

    df = df.with_row_index(name='')

    df.write_csv(os.path.join(PATH, 'dim_research_project.csv'))


async def fat_research_project_foment(session):
    data = await powerBi_repo.get_fat_research_project_foment(session)
    df_schema = {
        'project_id': pl.Utf8,
        'agency_name': pl.Utf8,
        'agency_code': pl.Utf8,
        'nature': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_research_project_foment.csv'))


async def dim_bibliographic_production_terms(session):
    import nltk

    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')
    stopwords += nltk.corpus.stopwords.words('portuguese')

    data = await powerBi_repo.get_dim_bibliographic_production_terms(
        session, stopwords
    )
    df_schema = {
        'id': pl.Utf8,
        'type_': pl.Utf8,
        'term': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_bibliographic_production_terms.csv'))


async def dim_tecnical_production_terms(session):
    import nltk

    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')
    stopwords += nltk.corpus.stopwords.words('portuguese')

    data = await powerBi_repo.get_dim_tecnical_production_terms(
        session, stopwords
    )
    df_schema = {
        'id': pl.Utf8,
        'type_': pl.Utf8,
        'term': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_tecnical_production_terms.csv'))


async def dim_logs_routine(session):
    data = await powerBi_repo.get_dim_logs_routine(session)
    df_schema = {
        'routine_type': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_logs_routine.csv'))


async def fat_event_organization(session):
    data = await powerBi_repo.get_fat_event_organization(session)
    df_schema = {
        'id': pl.Utf8,
        'title': pl.Utf8,
        'promoter_institution': pl.Utf8,
        'nature': pl.Utf8,
        'researcher_id': pl.Utf8,
        'local': pl.Utf8,
        'duration_in_weeks': pl.Utf8,
        'year': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_event_organization.csv'))


async def fat_participation_events(session):
    data = await powerBi_repo.get_fat_participation_events(session)
    df_schema = {
        'id': pl.Utf8,
        'title': pl.Utf8,
        'event_name': pl.Utf8,
        'nature': pl.Utf8,
        'form_participation': pl.Utf8,
        'type_participation': pl.Utf8,
        'researcher_id': pl.Utf8,
        'year': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_participation_events.csv'))


async def materialized_vision(session):
    data = await powerBi_repo.get_materialized_vision(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'search_term': pl.Utf8,
        'normalized_search_term': pl.Utf8,
        'type': pl.Utf8,
        'year': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(
        os.path.join(PATH, 'materialized_vision.csv'), quote_style='always'
    )


async def dim_article_keyword(session):
    import nltk

    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')
    stopwords += nltk.corpus.stopwords.words('portuguese')

    data = await powerBi_repo.get_dim_article_keyword(session, stopwords)
    df_schema = {
        'word': pl.Utf8,
        'frequency': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_article_keyword.csv'))


async def fat_article_keyword_(session):
    import nltk

    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')
    stopwords += nltk.corpus.stopwords.words('portuguese')

    data = await powerBi_repo.get_fat_article_keyword_(session, stopwords)
    df_schema = {
        'title': pl.Utf8,
        'word': pl.Utf8,
        'researcher_id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_article_keyword_.csv'))


async def fat_article_co_authorship(session):
    data = await powerBi_repo.get_fat_article_co_authorship(session)
    df_schema = {
        'title': pl.Utf8,
        'researcher_id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_article_co_authorship.csv'))


async def fat_keywords_cooccurrences(session):
    import nltk

    try:
        stopwords = nltk.corpus.stopwords.words('english')
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stopwords = nltk.corpus.stopwords.words('english')
    stopwords += nltk.corpus.stopwords.words('portuguese')

    data = await powerBi_repo.get_fat_keywords_cooccurrences(
        session, stopwords
    )
    df_schema = {
        'word1': pl.Utf8,
        'word2': pl.Utf8,
        'frequency': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_keywords_cooccurrences.csv'))


async def fat_co_authorship(session):
    data = await powerBi_repo.get_fat_co_authorship(session)
    df_schema = {
        'title': pl.Utf8,
        'researcher_id': pl.Utf8,
        'co_author': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_co_authorship.csv'))


async def guidance(session=None, admin_session=None):
    _ensure_static_file('guidance.csv')


async def supervisor(session=None, admin_session=None):
    _ensure_static_file('supervisor.csv')


async def guidance_per_year(session=None, admin_session=None):
    _ensure_static_file('guidance_per_year.csv')


async def in_progress_per_year(session=None, admin_session=None):
    _ensure_static_file('in_progress_per_year.csv')


async def dim_tags_csv(session=None, admin_session=None):
    _ensure_static_file('dim_tags.csv')


async def fat_tags_csv(session=None, admin_session=None):
    _ensure_static_file('fat_tags.csv')


async def ind_guidance_ori(session=None, admin_session=None):
    _ensure_static_file('ind_guidance_ori.csv')


async def ind_guidance_distori(session=None, admin_session=None):
    _ensure_static_file('ind_guidance_distori.csv')


async def ind_guidance_coaut(session=None, admin_session=None):
    _ensure_static_file('ind_guidance_coaut.csv')


async def fat_guidance_history(session=None, admin_session=None):
    _ensure_static_file('fat_guidance_history.csv')


async def dim_sdg(session):
    data = await powerBi_repo.get_dim_sdg(session)
    df_schema = {
        'id': pl.Utf8,
        'number': pl.Utf8,
        'name': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df.write_csv(
        os.path.join(PATH, 'dim_sdg.csv'), separator=';', quote_style='always'
    )


async def fat_sdg_articles(session):
    data = await powerBi_repo.get_fat_sdg_articles(session)
    df_schema = {
        'title': pl.Utf8,
        'researcher_id': pl.Utf8,
        'sdg_id': pl.Utf8,
        'year': pl.Utf8,
        'qualis': pl.Utf8,
        'periodical_magazine_id': pl.Utf8,
        'periodical_magazine_name': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df.write_csv(
        os.path.join(PATH, 'fat_sdg_articles.csv'),
        separator=';',
        quote_style='always',
    )


async def fat_sdg_alignment_researcher(session):
    data = await powerBi_repo.get_fat_sdg_alignment_researcher(session)
    df_schema = {
        'researcher_id': pl.Utf8,
        'sdg_number': pl.Utf8,
        'primary_sdg_name': pl.Utf8,
        'total_articles': pl.Utf8,
        'percentage': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_columns(
        pl.col('percentage').str.replace('.', ',', literal=True)
    )
    df.write_csv(
        os.path.join(PATH, 'fat_sdg_alignment_researcher.csv'),
        separator=';',
        quote_style='always',
    )


async def dim_territorio_identidade(session):
    print('dim_territorio_identidade')
    _ensure_static_file('dim_territorio_identidade.csv')


async def dim_log_category(session):
    from simcc.core.logging.constants import LogCategory

    data = [{'category': category.value} for category in LogCategory]
    df = pl.DataFrame(data, schema={'category': pl.Utf8})
    os.makedirs(PATH, exist_ok=True)
    df.write_csv(
        os.path.join(PATH, 'dim_log_category.csv'),
        separator=';',
        quote_style='always',
    )


async def dim_log_event(session):
    from simcc.core.logging.constants import LogEvent

    data = [{'event': event.value} for event in LogEvent]
    df = pl.DataFrame(data, schema={'event': pl.Utf8})
    os.makedirs(PATH, exist_ok=True)
    df.write_csv(
        os.path.join(PATH, 'dim_log_event.csv'),
        separator=';',
        quote_style='always',
    )


def _load_all_logs(log_dir: str):
    logs_data = []
    if not os.path.exists(log_dir):
        return logs_data

    idx = 0
    for file in sorted(os.listdir(log_dir)):
        if file.endswith('.jsonl'):
            filepath = os.path.join(log_dir, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                log_entry = json.loads(line)
                                log_entry['log_id'] = f'LOG_{idx}'
                                logs_data.append(log_entry)
                                idx += 1
                            except Exception:
                                pass
            except Exception:
                pass
    return logs_data


async def fat_logs(session):
    try:
        log_dir = Settings().LOG_DIR
    except Exception:
        log_dir = 'logs'

    logs = _load_all_logs(log_dir)
    rows = []
    for entry in logs:
        rows.append({
            'log_id': entry.get('log_id'),
            'timestamp': entry.get('timestamp'),
            'level': entry.get('level'),
            'application': entry.get('application'),
            'environment': entry.get('environment'),
            'hostname': entry.get('hostname'),
            'category': entry.get('category'),
            'event': entry.get('event'),
            'message': entry.get('message'),
            'request_id': entry.get('request_id'),
            'duration': entry.get('duration'),
        })

    df_schema = {
        'log_id': pl.Utf8,
        'timestamp': pl.Utf8,
        'level': pl.Utf8,
        'application': pl.Utf8,
        'environment': pl.Utf8,
        'hostname': pl.Utf8,
        'category': pl.Utf8,
        'event': pl.Utf8,
        'message': pl.Utf8,
        'request_id': pl.Utf8,
        'duration': pl.Float64,
    }

    if rows:
        for entry in rows:
            dur = entry.get('duration')
            if dur is not None:
                try:
                    entry['duration'] = float(dur)
                except ValueError:
                    entry['duration'] = None
        df = pl.DataFrame(rows, schema=df_schema)
    else:
        df = pl.DataFrame([], schema=df_schema)

    os.makedirs(PATH, exist_ok=True)
    df.write_csv(
        os.path.join(PATH, 'fat_logs.csv'),
        separator=';',
        quote_style='always',
    )


async def fat_logs_http(session):
    try:
        log_dir = Settings().LOG_DIR
    except Exception:
        log_dir = 'logs'

    logs = _load_all_logs(log_dir)
    rows = []
    for entry in logs:
        if entry.get('category') == 'http':
            data_dict = entry.get('data') or {}
            raw_status = data_dict.get('status_code')
            status_code = None
            if raw_status is not None:
                try:
                    status_code = int(raw_status)
                except (ValueError, TypeError):
                    status_code = None

            rows.append({
                'log_id': entry.get('log_id'),
                'route': data_dict.get('route'),
                'method': data_dict.get('method'),
                'status_code': status_code,
                'user_id': data_dict.get('user_id'),
                'error_message': data_dict.get('error_message'),
            })

    df_schema = {
        'log_id': pl.Utf8,
        'route': pl.Utf8,
        'method': pl.Utf8,
        'status_code': pl.Int64,
        'user_id': pl.Utf8,
        'error_message': pl.Utf8,
    }
    df = pl.DataFrame(rows, schema=df_schema)
    os.makedirs(PATH, exist_ok=True)
    df.write_csv(
        os.path.join(PATH, 'fat_logs_http.csv'),
        separator=';',
        quote_style='always',
    )


async def fat_logs_database(session):
    try:
        log_dir = Settings().LOG_DIR
    except Exception:
        log_dir = 'logs'

    logs = _load_all_logs(log_dir)
    rows = []
    for entry in logs:
        if entry.get('category') == 'database':
            data_dict = entry.get('data') or {}
            rows.append({
                'log_id': entry.get('log_id'),
                'database_name': data_dict.get('database_name'),
                'operation_name': data_dict.get('operation_name'),
                'error_message': data_dict.get('error_message'),
                'sql': data_dict.get('sql'),
            })

    df_schema = {
        'log_id': pl.Utf8,
        'database_name': pl.Utf8,
        'operation_name': pl.Utf8,
        'error_message': pl.Utf8,
        'sql': pl.Utf8,
    }
    df = pl.DataFrame(rows, schema=df_schema)
    os.makedirs(PATH, exist_ok=True)
    df.write_csv(
        os.path.join(PATH, 'fat_logs_database.csv'),
        separator=';',
        quote_style='always',
    )


async def fat_logs_routine(session):
    try:
        log_dir = Settings().LOG_DIR
    except Exception:
        log_dir = 'logs'

    logs = _load_all_logs(log_dir)
    rows = []
    for entry in logs:
        if entry.get('category') == 'routine':
            data_dict = entry.get('data') or {}

            # Safely cast metrics to int/None
            items_found = data_dict.get('items_found')
            if items_found is not None:
                try:
                    items_found = int(items_found)
                except (ValueError, TypeError):
                    items_found = None

            items_succeeded = data_dict.get('items_succeeded')
            if items_succeeded is not None:
                try:
                    items_succeeded = int(items_succeeded)
                except (ValueError, TypeError):
                    items_succeeded = None

            items_failed = data_dict.get('items_failed')
            if items_failed is not None:
                try:
                    items_failed = int(items_failed)
                except (ValueError, TypeError):
                    items_failed = None

            rows.append({
                'log_id': entry.get('log_id'),
                'routine_name': data_dict.get('routine_name'),
                'error_message': data_dict.get('error_message'),
                'items_found': items_found,
                'items_succeeded': items_succeeded,
                'items_failed': items_failed,
            })

    df_schema = {
        'log_id': pl.Utf8,
        'routine_name': pl.Utf8,
        'error_message': pl.Utf8,
        'items_found': pl.Int64,
        'items_succeeded': pl.Int64,
        'items_failed': pl.Int64,
    }
    df = pl.DataFrame(rows, schema=df_schema)
    os.makedirs(PATH, exist_ok=True)
    df = df.with_row_index(name='')
    df.write_csv(
        os.path.join(PATH, 'fat_logs_routine.csv'),
        quote_style='always',
    )
