import json
import os
import shutil
from datetime import date, datetime

import polars as pl

from simcc.core.settings import Settings
from simcc.v1.repositories import powerBi_repo

PATH = 'storage/powerBI'


def _ensure_static_file(filename):
    dest_path = os.path.join(PATH, filename)
    if not os.path.exists(dest_path):
        src_path = os.path.join('storage/powerBI', filename)
        if os.path.exists(src_path):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy(src_path, dest_path)


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


async def researcher_area_leader(session, admin_session):
    data_admin = await powerBi_repo.get_researcher_area_leader(admin_session)
    data_main = await powerBi_repo.get_researcher_area_leader_researcher(
        session
    )

    df_admin = pl.DataFrame(
        data_admin,
        schema={
            'lattes_id': pl.Utf8,
            'area_leader': pl.Utf8,
            'focal_point': pl.Utf8,
        },
    )
    df_main = pl.DataFrame(
        data_main,
        schema={
            'researcher_id': pl.Utf8,
            'lattes_id': pl.Utf8,
        },
    )

    df = df_admin.join(df_main, on='lattes_id', how='left')
    df = df.select(['researcher_id', 'area_leader', 'focal_point'])
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'researcher_area_leader.csv'))


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


async def _guidance(session, admin_session):
    data_guidance = await powerBi_repo.get_guidance(admin_session)
    data_researchers = await powerBi_repo.get_guidance_researcher(session)

    df_guidance = pl.DataFrame(
        data_guidance,
        schema={
            'id': pl.Utf8,
            'student_lattes_id': pl.Utf8,
            'supervisor_lattes_id': pl.Utf8,
            'co_supervisor_lattes_id': pl.Utf8,
            'graduate_program_id': pl.Utf8,
            'start_date': pl.Utf8,
            'planned_date_project': pl.Utf8,
            'done_date_project': pl.Utf8,
            'planned_date_qualification': pl.Utf8,
            'done_date_qualification': pl.Utf8,
            'planned_date_conclusion': pl.Utf8,
            'done_date_conclusion': pl.Utf8,
            'student_name': pl.Utf8,
            'supervisor_name': pl.Utf8,
            'co_name': pl.Utf8,
            'type': pl.Utf8,
        },
    )

    df_researchers = pl.DataFrame(
        data_researchers,
        schema={
            'researcher_id': pl.Utf8,
            'lattes_id': pl.Utf8,
        },
    )

    df = df_guidance.join(
        df_researchers.select(['researcher_id', 'lattes_id']).rename({
            'researcher_id': 'student_researcher_id'
        }),
        left_on='student_lattes_id',
        right_on='lattes_id',
        how='left',
    )
    df = df.join(
        df_researchers.select(['researcher_id', 'lattes_id']).rename({
            'researcher_id': 'supervisor_researcher_id'
        }),
        left_on='supervisor_lattes_id',
        right_on='lattes_id',
        how='left',
    )
    df = df.join(
        df_researchers.select(['researcher_id', 'lattes_id']).rename({
            'researcher_id': 'co_supervisor_researcher_id'
        }),
        left_on='co_supervisor_lattes_id',
        right_on='lattes_id',
        how='left',
    )
    return df


async def supervisor(session, admin_session):
    df_original = await _guidance(session, admin_session)

    df_original = df_original.with_columns(
        pl
        .col('planned_date_conclusion')
        .str.to_date(strict=False)
        .dt.year()
        .alias('year')
    ).filter(pl.col('year').is_not_null())

    df_original = df_original.select(['year', 'supervisor_researcher_id'])

    df_min_max = (
        df_original
        .group_by('supervisor_researcher_id')
        .agg(
            pl.col('year').min().alias('min_year'),
            pl.col('year').max().alias('max_year'),
        )
        .filter(
            pl.col('min_year').is_not_null() & pl.col('max_year').is_not_null()
        )
    )

    df_expanded = (
        df_min_max
        .with_columns(
            pl.int_ranges('min_year', pl.col('max_year') + 1).alias('year')
        )
        .explode('year')
        .select(['supervisor_researcher_id', 'year'])
    )

    df_counts = df_original.group_by(['supervisor_researcher_id', 'year']).len(
        name='ended_in_year'
    )

    df_joined = df_expanded.join(
        df_counts, on=['supervisor_researcher_id', 'year'], how='left'
    ).fill_null(0)

    df_sorted = df_joined.sort(
        ['supervisor_researcher_id', 'year'], descending=[False, True]
    )
    df_sorted = df_sorted.with_columns(
        pl
        .col('ended_in_year')
        .cum_sum()
        .over('supervisor_researcher_id')
        .cast(pl.Int64)
        .alias('count')
    )

    df_final = df_sorted.select([
        'supervisor_researcher_id',
        'year',
        'count',
    ]).sort(['supervisor_researcher_id', 'year'])
    df_final = df_final.with_row_index(name='')
    df_final.write_csv(os.path.join(PATH, 'supervisor.csv'))


async def guidance(session, admin_session):
    df_polars = await _guidance(session, admin_session)
    rows = df_polars.iter_rows(named=True)
    today = datetime.now().date()

    new_rows = []
    for r in rows:
        row = dict(r)
        row['program_type'] = row.pop('type', None)

        done_date_conclusion = parse_date(row['done_date_conclusion'])
        planned_date_conclusion = parse_date(row['planned_date_conclusion'])
        done_date_qualification = parse_date(row['done_date_qualification'])
        planned_date_qualification = parse_date(
            row['planned_date_qualification']
        )
        done_date_project = parse_date(row['done_date_project'])
        planned_date_project = parse_date(row['planned_date_project'])
        start_date = parse_date(row['start_date'])

        delays = []
        if done_date_conclusion is None:
            if (
                planned_date_conclusion is not None
                and planned_date_conclusion < today
            ):
                delays.append((today - planned_date_conclusion).days)
        if done_date_qualification is None:
            if (
                planned_date_qualification is not None
                and planned_date_qualification < today
            ):
                delays.append((today - planned_date_qualification).days)
        if done_date_project is None:
            if (
                planned_date_project is not None
                and planned_date_project < today
            ):
                delays.append((today - planned_date_project).days)

        ped_days = 0
        if delays:
            ped_days = max(delays)
        elif planned_date_conclusion is not None:
            ped_days = (planned_date_conclusion - today).days

        ped_days_ = max(delays) if delays else 0
        row['peding_days'] = str(ped_days)
        row['peding'] = 'EM ATRASO' if ped_days_ > 0 else 'EM DIA'

        if done_date_project is None:
            t = 'PROJETO'
        elif done_date_qualification is None:
            t = 'QUALIFICAÇÃO'
        elif done_date_conclusion is None:
            t = 'CONCLUSÃO'
        else:
            t = 'FINALIZADO'
        row['type'] = t

        days_offset = None
        if done_date_conclusion is not None and start_date is not None:
            days_offset = (done_date_conclusion - start_date).days
        elif planned_date_conclusion is not None and start_date is not None:
            days_offset = (planned_date_conclusion - start_date).days
        row['days_offset'] = (
            str(days_offset) if days_offset is not None else ''
        )

        new_rows.append(row)

    df_new = pl.DataFrame(new_rows)
    if not df_new.is_empty():
        df_new = df_new.with_row_index(name='')
    df_new.write_csv(os.path.join(PATH, 'guidance.csv'), quote_style='always')


async def guidance_per_year(session, admin_session):
    df_polars = await _guidance(session, admin_session)
    rows = df_polars.iter_rows(named=True)

    new_rows = []
    for r in rows:
        row_orig = dict(r)
        row_orig['program_type'] = row_orig.pop('type', None)

        done_date_conclusion = parse_date(row_orig['done_date_conclusion'])
        planned_date_conclusion = parse_date(
            row_orig['planned_date_conclusion']
        )
        done_date_qualification = parse_date(
            row_orig['done_date_qualification']
        )
        planned_date_qualification = parse_date(
            row_orig['planned_date_qualification']
        )
        done_date_project = parse_date(row_orig['done_date_project'])
        planned_date_project = parse_date(row_orig['planned_date_project'])

        t_list = []
        if done_date_project is None:
            t_list = ['PROJETO']
        else:
            t_list.append('PROJETO')
            if done_date_qualification is not None:
                t_list.append('QUALIFICAÇÃO')
                if done_date_conclusion is None:
                    t_list.append('DEFESA')
            if done_date_conclusion is not None:
                t_list = ['FINALIZADO']

        for t in t_list:
            row = dict(row_orig)
            row['type'] = t
            row['status'] = 'FINALIZADO' if t == 'FINALIZADO' else 'EM CURSO'

            if t == 'PROJETO':
                row['status_'] = (
                    'REALIZADO'
                    if done_date_project is not None
                    else 'EM ANDAMENTO'
                )
            elif t == 'QUALIFICAÇÃO':
                row['status_'] = (
                    'REALIZADO'
                    if done_date_qualification is not None
                    else 'EM ANDAMENTO'
                )
            elif t == 'DEFESA':
                row['status_'] = (
                    'REALIZADO'
                    if done_date_conclusion is not None
                    else 'EM ANDAMENTO'
                )
            elif t == 'FINALIZADO':
                row['status_'] = 'REALIZADO'
            else:
                row['status_'] = 'EM ANDAMENTO'

            year_val = None
            if t == 'PROJETO':
                dt = done_date_project or planned_date_project
                year_val = dt.year if dt else None
            elif t == 'QUALIFICAÇÃO':
                dt = done_date_qualification or planned_date_qualification
                year_val = dt.year if dt else None
            elif t in {'DEFESA', 'FINALIZADO'}:
                dt = done_date_conclusion or planned_date_conclusion
                year_val = dt.year if dt else None
            row['year'] = str(year_val) if year_val else ''

            row['in_progress'] = (
                'FINALIZADO'
                if (t == 'FINALIZADO' and row['status_'] == 'REALIZADO')
                else 'EM CURSO'
            )

            new_rows.append(row)

    new_rows.sort(key=lambda x: x.get('student_name') or '')

    columns = [
        'id',
        'graduate_program_id',
        'student_name',
        'student_researcher_id',
        'supervisor_name',
        'supervisor_researcher_id',
        'co_name',
        'co_supervisor_researcher_id',
        'type',
        'status_',
        'year',
        'in_progress',
    ]
    df_new = pl.DataFrame(new_rows)
    if not df_new.is_empty():
        df_new = df_new.select(columns)
        df_new = df_new.with_row_index(name='')
    df_new.write_csv(
        os.path.join(PATH, 'guidance_per_year.csv'), quote_style='always'
    )


async def in_progress_per_year(session, admin_session):
    df_polars = await _guidance(session, admin_session)
    rows = df_polars.iter_rows(named=True)

    exploded_list = []
    for r in rows:
        row_orig = dict(r)
        row_orig['program_type'] = row_orig.pop('type', None)

        done_date_conclusion = parse_date(row_orig['done_date_conclusion'])
        planned_date_conclusion = parse_date(
            row_orig['planned_date_conclusion']
        )
        done_date_qualification = parse_date(
            row_orig['done_date_qualification']
        )
        planned_date_qualification = parse_date(
            row_orig['planned_date_qualification']
        )
        done_date_project = parse_date(row_orig['done_date_project'])
        planned_date_project = parse_date(row_orig['planned_date_project'])

        t_list = []
        if done_date_project is None:
            t_list = ['PROJETO']
        else:
            t_list.append('PROJETO')
            if done_date_qualification is not None:
                t_list.append('QUALIFICAÇÃO')
                if done_date_conclusion is None:
                    t_list.append('DEFESA')
            if done_date_conclusion is not None:
                t_list = ['FINALIZADO']

        for t in t_list:
            row = dict(row_orig)
            row['type'] = t

            if t == 'PROJETO':
                status_val = (
                    'REALIZADO'
                    if done_date_project is not None
                    else 'EM ANDAMENTO'
                )
            elif t == 'QUALIFICAÇÃO':
                status_val = (
                    'REALIZADO'
                    if done_date_qualification is not None
                    else 'EM ANDAMENTO'
                )
            elif t == 'DEFESA':
                status_val = (
                    'REALIZADO'
                    if done_date_conclusion is not None
                    else 'EM ANDAMENTO'
                )
            elif t == 'FINALIZADO':
                status_val = 'REALIZADO'
            else:
                status_val = 'EM ANDAMENTO'

            year_val = None
            if t == 'PROJETO':
                dt = done_date_project or planned_date_project
                year_val = dt.year if dt else None
            elif t == 'QUALIFICAÇÃO':
                dt = done_date_qualification or planned_date_qualification
                year_val = dt.year if dt else None
            elif t in {'DEFESA', 'FINALIZADO'}:
                dt = done_date_conclusion or planned_date_conclusion
                year_val = dt.year if dt else None

            if year_val is not None:
                row['year'] = int(year_val)
                row['in_progress'] = (
                    'FINALIZADO'
                    if (t == 'FINALIZADO' and status_val == 'REALIZADO')
                    else 'EM CURSO'
                )
                exploded_list.append(row)

    if not exploded_list:
        df_new = pl.DataFrame(
            [],
            schema={
                'in_progress': pl.Utf8,
                'year': pl.Int64,
                'supervisor_name': pl.Utf8,
                'supervisor_researcher_id': pl.Utf8,
                'graduate_program_id': pl.Utf8,
                'count': pl.Int64,
            },
        )
        df_new.write_csv(os.path.join(PATH, 'in_progress_per_year.csv'))
        return

    supervisors = set()
    years = set()
    statuses = set()
    programs = set()
    for item in exploded_list:
        supervisors.add((
            item['supervisor_name'],
            item['supervisor_researcher_id'],
        ))
        years.add(item['year'])
        statuses.add(item['in_progress'])
        programs.add(item['graduate_program_id'])

    if years:
        min_year = min(years)
        max_year = max(years)
        years_range = list(range(min_year, max_year + 1))
    else:
        years_range = []

    counts_map = {}
    for item in exploded_list:
        key = (
            item['supervisor_name'],
            item['supervisor_researcher_id'],
            item['year'],
            item['in_progress'],
            item['graduate_program_id'],
        )
        counts_map[key] = counts_map.get(key, 0) + 1

    result_list = []
    for sup_name, sup_id in supervisors:
        for yr in years_range:
            for st in statuses:
                for prog in programs:
                    key = (sup_name, sup_id, yr, st, prog)
                    cnt = counts_map.get(key, 0)
                    result_list.append({
                        'supervisor_name': sup_name,
                        'supervisor_researcher_id': sup_id,
                        'year': yr,
                        'in_progress': st,
                        'graduate_program_id': prog,
                        'count': cnt,
                    })

    result_list.sort(
        key=lambda x: (
            x.get('supervisor_name') or '',
            x.get('year') or 0,
            x.get('graduate_program_id') or '',
            x.get('in_progress') or '',
        )
    )

    df_result = pl.DataFrame(result_list)
    df_result.write_csv(os.path.join(PATH, 'in_progress_per_year.csv'))


async def dim_tags_csv(session, admin_session):
    data = await powerBi_repo.get_dim_tags(admin_session)
    df_schema = {
        'id': pl.Utf8,
        'name': pl.Utf8,
        'color_code': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'dim_tags.csv'), quote_style='always')


async def fat_tags_csv(session, admin_session):
    data = await powerBi_repo.get_fat_tags(admin_session)
    df_schema = {
        'guidance_tracking_id': pl.Utf8,
        'tag_id': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.with_row_index(name='')
    df.write_csv(os.path.join(PATH, 'fat_tags.csv'), quote_style='always')


async def ind_guidance_ori(session, admin_session):
    data = await powerBi_repo.get_ind_guidance_ori(admin_session)
    df_schema = {
        'graduate_program_id': pl.Utf8,
        'year': pl.Utf8,
        'masters_defenses': pl.Utf8,
        'doctorate_defenses': pl.Utf8,
        'permanent_researchers': pl.Utf8,
        'ind_ori': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.filter(pl.col('year').is_not_null())
    df = df.with_columns(
        pl.col('year').cast(pl.Int64, strict=False).cast(pl.Utf8)
    )
    df = df.with_columns(pl.col('ind_ori').str.replace('.', ',', literal=True))
    df = df.with_row_index(name='')
    df.write_csv(
        os.path.join(PATH, 'ind_guidance_ori.csv'),
        quote_style='always',
    )


async def ind_guidance_coaut(session, admin_session):
    data_prog = await powerBi_repo.get_ind_guidance_coaut_prog(admin_session)
    data_prod = await powerBi_repo.get_ind_guidance_coaut_prod(session)

    prog_rows = [dict(r) for r in data_prog]
    prod_rows = [dict(r) for r in data_prod]

    prod_filtered = []
    for r in prod_rows:
        if r.get('identifier') and r.get('year'):
            try:
                r['year'] = int(r['year'])
                prod_filtered.append(r)
            except Exception:
                pass

    prog_by_res = {}
    for pr in prog_rows:
        res_id = pr['researcher_id']
        prog_by_res.setdefault(res_id, []).append(pr['graduate_program_id'])

    merged = []
    for pr in prod_filtered:
        res_id = pr['researcher_id']
        if res_id in prog_by_res:
            for gp_id in prog_by_res[res_id]:
                item = dict(pr)
                item['graduate_program_id'] = gp_id
                merged.append(item)

    coaut_count = {}
    for item in merged:
        key = (item['identifier'], item['type'])
        coaut_count.setdefault(key, set()).add(item['researcher_id'])

    coaut_keys = {
        key for key, res_set in coaut_count.items() if len(res_set) > 1
    }

    df_filtered = [
        item
        for item in merged
        if (item['identifier'], item['type']) in coaut_keys
    ]

    seen = set()
    df_unique = []
    for item in df_filtered:
        key = (item['graduate_program_id'], item['identifier'], item['type'])
        if key not in seen:
            seen.add(key)
            df_unique.append(item)

    counts = {}
    for item in df_unique:
        key = (item['graduate_program_id'], item['type'], item['year'])
        counts[key] = counts.get(key, 0) + 1

    index_keys = sorted(list({(key[0], key[2]) for key in counts.keys()}))

    pivot_rows = []
    for gp_id, yr in index_keys:
        art_count = counts.get((gp_id, 'ARTICLE', yr), 0)
        book_count = counts.get((gp_id, 'BOOK', yr), 0)
        chapter_count = counts.get((gp_id, 'BOOK_CHAPTER', yr), 0)
        pivot_rows.append({
            'graduate_program_id': gp_id,
            'year': yr,
            'IndProdArtCoAut': art_count,
            'IndProdLivCoAut': book_count,
            'IndProdCapCoAut': chapter_count,
        })

    df_new = pl.DataFrame(pivot_rows)
    df_new.write_csv(
        os.path.join(PATH, 'ind_guidance_coaut.csv'), quote_style='always'
    )


async def ind_guidance_distori(session, admin_session):
    data = await powerBi_repo.get_ind_guidance_distori(admin_session)
    df_schema = {
        'graduate_program_id': pl.Utf8,
        'year': pl.Utf8,
        'concluding_researchers': pl.Utf8,
        'permanent_researchers': pl.Utf8,
        'ind_dist_ori': pl.Utf8,
    }
    df = pl.DataFrame(data, schema=df_schema)
    df = df.filter(pl.col('year').is_not_null())
    df = df.with_columns(
        pl.col('year').cast(pl.Int64, strict=False).cast(pl.Utf8)
    )
    df = df.with_columns(
        pl.col('ind_dist_ori').str.replace('.', ',', literal=True)
    )
    df = df.with_row_index(name='')
    df.write_csv(
        os.path.join(PATH, 'ind_guidance_distori.csv'),
        quote_style='always',
    )


async def fat_guidance_history(session, admin_session):
    data_history = await powerBi_repo.get_fat_guidance_history(admin_session)
    df_researcher_map = await powerBi_repo.get_guidance_researcher(session)

    res_map = {
        r['lattes_id']: r['id']
        for r in df_researcher_map
        if r.get('lattes_id')
    }

    history_joined = []
    for h in data_history:
        h_dict = dict(h)
        student_lattes = h_dict.get('student_lattes_id')
        supervisor_lattes = h_dict.get('supervisor_lattes_id')

        if student_lattes in res_map:
            h_dict['student_id'] = res_map[student_lattes]
            h_dict['supervisor_id'] = res_map.get(supervisor_lattes, '')
            history_joined.append(h_dict)

    history_dates = []
    for h in history_joined:
        start_date = parse_date(h['start_date'])
        done_date_conclusion = parse_date(h['done_date_conclusion'])
        planned_date_conclusion = parse_date(h['planned_date_conclusion'])

        end_date = (
            done_date_conclusion
            if done_date_conclusion is not None
            else planned_date_conclusion
        )

        if start_date is not None and end_date is not None:
            h['start_year'] = start_date.year
            h['end_year'] = end_date.year
            h['done_year'] = (
                done_date_conclusion.year
                if done_date_conclusion is not None
                else None
            )
            history_dates.append(h)

    exploded = []
    for h in history_dates:
        start_yr = h['start_year']
        end_yr = h['end_year']
        done_yr = h['done_year']

        for yr in range(start_yr, end_yr + 1):
            exploded.append({
                'student_name': h['student_name'],
                'student_id': h['student_id'],
                'supervisor_id': h['supervisor_id'],
                'year': yr,
                'done_year': done_yr,
            })

    current_year = datetime.now().year

    final_rows = []
    for item in exploded:
        yr = item['year']
        done_yr = item['done_year']

        if done_yr is not None and yr == done_yr:
            t = 'CONCLUÍDO'
        elif yr >= current_year:
            t = 'EXPECTATIVA'
        else:
            t = 'EM ANDAMENTO'

        final_rows.append({
            'student_name': item['student_name'],
            'student_id': item['student_id'],
            'supervisor_id': item['supervisor_id'],
            'year': yr,
            'type': t,
        })

    df_new = pl.DataFrame(final_rows)
    if not df_new.is_empty():
        df_new = df_new.with_row_index(name='')
    df_new.write_csv(
        os.path.join(PATH, 'fat_guidance_history.csv'), quote_style='always'
    )


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
            rows.append({
                'log_id': entry.get('log_id'),
                'route': data_dict.get('route'),
                'method': data_dict.get('method'),
                'user_id': data_dict.get('user_id'),
                'error_message': data_dict.get('error_message'),
            })

    df_schema = {
        'log_id': pl.Utf8,
        'route': pl.Utf8,
        'method': pl.Utf8,
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
