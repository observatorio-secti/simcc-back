from pathlib import Path
from typing import Any

import polars as pl

from simcc.core.utils import (
    DEFAULT_AVATAR_PATH,
    download_researcher_image,
    get_institution_cover_url,
    get_institution_logo_url,
)
from simcc.repositories import researcher_repo
from simcc.schemas.common import PaginationParams


async def search_researchers(
    session,
    filters,
    search_type=None,
    name=None,
    pagination: PaginationParams = None,
):

    if search_type == 'FOMENT' and not filters.modality:
        filters.modality = '*'

    researchers = await researcher_repo.search_researchers(
        session, filters, search_type, name, pagination
    )

    if researchers:
        researchers = await enrich_researchers(session, researchers)

    return researchers


def _normalize_researcher_dict(r: Any) -> dict[str, Any]:
    if hasattr(r, 'model_dump'):
        return r.model_dump()
    if hasattr(r, '_asdict'):
        return r._asdict()
    if not isinstance(r, dict) and hasattr(r, 'get'):
        return dict(r)
    return r if isinstance(r, dict) else {}


def _build_institution_map(inst_data: list) -> dict[str, dict[str, Any]]:
    inst_map = {}
    for row in inst_data:
        rid = str(row['id'])
        attrs = dict(row.get('custom_attributes') or {})
        if row.get('gender') is not None:
            attrs['gender'] = row['gender']
        if row.get('zip_code') is not None:
            attrs['zip_code'] = row['zip_code']
        if row.get('work_regime') is not None:
            attrs['work_regime'] = row['work_regime']
        inst_map[rid] = attrs
    return inst_map


def _build_institution_objects_map(
    inst_rows: list,
) -> dict[str, dict[str, Any]]:
    obj_map = {}
    for row in inst_rows:
        iid = str(row['id'])
        acronym = row.get('acronym')
        logo_url = get_institution_logo_url(acronym) or (
            row.get('image') if row.get('image') else None
        )
        cover_url = get_institution_cover_url(acronym)
        obj_map[iid] = {
            'id': row['id'],
            'name': row.get('name'),
            'acronym': acronym,
            'image': logo_url,
            'cover': cover_url,
        }
    return obj_map


def _enrich_institution_dict(inst: Any) -> dict[str, Any]:
    d = dict(inst) if not isinstance(inst, dict) else dict(inst)
    acronym = d.get('acronym')
    logo_url = get_institution_logo_url(acronym) or d.get('image')
    cover_url = get_institution_cover_url(acronym)
    d['image'] = logo_url
    d['cover'] = cover_url
    return d


async def enrich_researchers(session, researchers: list):
    if not researchers:
        return researchers

    processed = [_normalize_researcher_dict(r) for r in researchers]
    researcher_ids = [r['id'] for r in processed if r.get('id')]
    lattes_ids = [r['lattes_id'] for r in processed if r.get('lattes_id')]
    inst_ids = [
        r['institution_id'] for r in processed if r.get('institution_id')
    ]

    if not researcher_ids:
        return processed

    # Consultas em lote
    gp_data = await researcher_repo.list_graduate_programs_by_ids(
        session, researcher_ids
    )
    rg_data = await researcher_repo.list_research_groups_by_ids(
        session, researcher_ids
    )
    subsidy_data = await researcher_repo.list_subsidy_by_ids(
        session, researcher_ids
    )
    dep_data = await researcher_repo.list_departments_by_ids(
        session, researcher_ids
    )
    ufmg_data = await researcher_repo.list_ufmg_data_by_ids(
        session, researcher_ids
    )
    user_data = await researcher_repo.list_user_data_by_lattes_ids(
        session, lattes_ids
    )
    inst_data = await researcher_repo.list_institution_data_by_researcher_ids(
        session, researcher_ids
    )
    inst_obj_data = await researcher_repo.list_institutions_by_ids(
        session, inst_ids
    )
    link_data = {str(row['id']): row for row in inst_data}
    # Mapeamentos
    maps = {
        'gp': {str(row['id']): row['graduate_programs'] for row in gp_data},
        'rg': {str(row['id']): row['research_groups'] for row in rg_data},
        'subsidy': {str(row['id']): row['subsidy'] for row in subsidy_data},
        'dep': {str(row['id']): row['departments'] for row in dep_data},
        'ufmg': {str(row['id']): dict(row) for row in ufmg_data},
        'user': {str(row['lattes_id']): row['user'] for row in user_data},
        'inst': _build_institution_map(inst_data),
        'inst_obj': _build_institution_objects_map(inst_obj_data),
    }

    # Aplica dados
    for r in processed:
        rid = str(r['id']) if r.get('id') is not None else None
        lid = str(r['lattes_id']) if r.get('lattes_id') is not None else None
        inst_id = (
            str(r['institution_id'])
            if r.get('institution_id') is not None
            else None
        )

        r['graduate_programs'] = maps['gp'].get(rid, [])
        r['research_groups'] = maps['rg'].get(rid, [])
        r['subsidy'] = maps['subsidy'].get(rid, [])
        r['departments'] = maps['dep'].get(rid, [])
        r['ufmg'] = maps['ufmg'].get(rid)
        r['user'] = maps['user'].get(lid)
        r['custom_attributes'] = maps['inst'].get(rid, None)

        if inst_id and inst_id in maps['inst_obj']:
            r['institution'] = dict(maps['inst_obj'][inst_id])
        elif r.get('institution_id') or r.get('university'):
            acronym = r.get('university')
            logo_url = get_institution_logo_url(acronym) or r.get(
                'image_university'
            )
            cover_url = get_institution_cover_url(acronym)
            r['institution'] = {
                'id': r.get('institution_id'),
                'name': r.get('university'),
                'acronym': acronym,
                'image': logo_url,
                'cover': cover_url,
            }
        else:
            r['institution'] = None

        if r.get('institution'):
            link = link_data.get(rid, {})
            r['institution']['territorio_identidade'] = link.get(
                'territorio_identidade'
            )
            r['institution']['carga_horaria'] = link.get('carga_horaria')

        if r.get('institution') and r['institution'].get('image'):
            r['image_university'] = r['institution']['image']

    if len(researchers) == len(processed):
        for i in range(len(researchers)):
            researchers[i] = processed[i]

    return processed


async def get_metrics_academic_degree(session, filters):
    return await researcher_repo.get_metrics_academic_degree(session, filters)


async def get_metrics_great_area(session, filters):
    return await researcher_repo.get_metrics_great_area(session, filters)


async def get_metrics_yearly_production(session, filters, production_type):
    return await researcher_repo.get_metrics_yearly_production(
        session, filters, production_type
    )


async def get_metrics_researcher(session, filters):
    return await researcher_repo.get_metrics_researcher(session, filters)


async def get_metrics_patents(session, filters):
    return await researcher_repo.get_metrics_patents(session, filters)


async def get_metrics_guidance(session, filters):
    return await researcher_repo.get_metrics_guidance(session, filters)


async def get_metrics_speaker(session, filters):
    return await researcher_repo.get_metrics_speaker(session, filters)


async def get_metrics_education(session, filters):
    return await researcher_repo.get_metrics_education(session, filters)


async def get_metrics_software(session, filters):
    return await researcher_repo.get_metrics_software(session, filters)


async def get_metrics_research_report(session, filters):
    return await researcher_repo.get_metrics_research_report(session, filters)


async def get_metrics_brand(session, filters, nature=None):
    return await researcher_repo.get_metrics_brand(
        session, filters, nature=nature
    )


async def get_metrics_research_project(session, filters):
    return await researcher_repo.get_metrics_research_project(session, filters)


async def get_metrics_lattes_update(session, filters):
    return await researcher_repo.get_metrics_lattes_update(session, filters)


async def get_metrics_scholarship(session, filters):
    return await researcher_repo.get_metrics_scholarship(session, filters)


async def get_metrics_magazine(session, issn=None, initials=None):
    return await researcher_repo.get_metrics_magazine(
        session, issn=issn, initials=initials
    )


async def list_labs(session, lattes_id=None, researcher_id=None):
    return await researcher_repo.list_labs(session, lattes_id, researcher_id)


async def list_institutions(session):
    data = await researcher_repo.list_institutions(session)
    return [_enrich_institution_dict(inst) for inst in data]


async def get_institution(session, institution_id):
    data = await researcher_repo.get_institution(session, institution_id)
    return _enrich_institution_dict(data) if data else None


async def list_researcher_terms(session, filters):
    return await researcher_repo.list_researcher_terms(session, filters)


async def list_original_words(session, initials, type_):
    data = await researcher_repo.list_original_words(session, initials, type_)

    return [
        {
            'term': str(row['term']).capitalize(),
            'frequency': str(row['frequency']),
            'type': str(row['type']),
            'checkbox': 0,
        }
        for row in data
    ]


async def list_institution_frequency(session, terms, institution, type_):
    data = await researcher_repo.list_institution_frequency(
        session, terms, institution, type_
    )

    return [
        {
            'id': str(row['id']),
            'institution': str(row['institution']),
            'among': str(row['qtd']),
            'image': str(row['image']) if row['image'] else None,
        }
        for row in data
    ]


async def list_co_authorship(session, researcher_id):
    co_authors_data = await researcher_repo.list_co_authorship(
        session, researcher_id
    )

    if not co_authors_data:
        return []

    researcher = await researcher_repo.get_researcher(session, researcher_id)
    if not researcher:
        return []

    researcher_institution_name = researcher.get('university')
    researcher_name = researcher.get('name')

    df = pl.DataFrame(co_authors_data)

    df = df.with_columns(
        pl
        .when(pl.col('institution') == researcher_institution_name)
        .then(pl.lit('internal'))
        .otherwise(pl.lit('external'))
        .alias('type')
    )

    df = df.with_columns(
        pl
        .col('name')
        .map_elements(
            lambda name: (
                ''.join(w[0] for w in str(name).replace('.', '').split() if w)
                if name is not None
                else ''
            ),
            return_dtype=pl.String,
        )
        .alias('initials')
    )

    df = df.group_by(['name', 'initials']).agg([
        pl.col('among').sum().alias('among'),
        pl
        .when((pl.col('type') == 'internal').any())
        .then(pl.lit('internal'))
        .otherwise(pl.lit('external'))
        .alias('type'),
    ])

    df = df.filter(pl.col('name') != researcher_name)

    return df.to_dicts()


async def get_departament_rt(session):
    return await researcher_repo.get_departament_rt(session)


async def get_researcher_id_by_params(
    session, lattes_id=None, name=None, researcher_id=None
):
    return await researcher_repo.get_researcher_id(
        session, lattes_id=lattes_id, name=name, researcher_id=researcher_id
    )


async def get_researcher_image_path(session, researcher_id):
    path_image = Path(f'storage/image_researcher/{researcher_id}.jpg')

    if not path_image.exists():
        await download_researcher_image(researcher_id, session=session)

    if not path_image.exists():
        return str(DEFAULT_AVATAR_PATH)

    return str(path_image)


async def get_researcher_filter(session):
    return await researcher_repo.get_researcher_filter(session)


async def get_outstanding_researchers(
    session, limit: int = 10, pool_size: int = 100
):
    researchers = await researcher_repo.get_outstanding_researchers(
        session, limit=limit, pool_size=pool_size
    )

    if researchers:
        await enrich_researchers(session, researchers)

    return researchers
