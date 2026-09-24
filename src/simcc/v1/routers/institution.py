from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from simcc.core.dependencies import AsyncSession
from simcc.core.utils import (
    get_institution_cover_path,
    get_institution_logo_path,
)
from simcc.v1.schemas.institution import Institution, InstitutionMetric
from simcc.v1.services import researcher_service

router = APIRouter(tags=['Institution'])


@router.get('/institution', response_model=list[Institution])
async def list_institutions(session: AsyncSession):
    return await researcher_service.list_institutions(session)


@router.get(
    '/institution/production-frequency', response_model=list[InstitutionMetric]
)
@router.get('/institutionFrequenci', include_in_schema=False)
async def list_institution_frequency(
    session: AsyncSession,
    terms: str | None = Query(None),
    university: str | None = Query(None),
    type: str = Query(...),
):
    return await researcher_service.list_institution_frequency(
        session, terms, university, type
    )


@router.get('/institution/image')
@router.get('/institution/image/{acronym}')
async def get_institution_image(
    session: AsyncSession,
    acronym: str | None = None,
    institution_id: UUID | None = Query(None),
):
    resolved_acronym = acronym
    if not resolved_acronym and institution_id:
        inst = await researcher_service.get_institution(
            session, institution_id
        )
        if inst:
            resolved_acronym = inst.get('acronym')

    if not resolved_acronym:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Acrônimo ou ID da instituição não informado',
        )

    path = get_institution_logo_path(resolved_acronym)
    if not path or not path.exists():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Imagem da instituição não encontrada',
        )

    return FileResponse(path)


@router.get('/institution/cover')
@router.get('/institution/cover/{acronym}')
async def get_institution_cover(
    session: AsyncSession,
    acronym: str | None = None,
    institution_id: UUID | None = Query(None),
):
    resolved_acronym = acronym
    if not resolved_acronym and institution_id:
        inst = await researcher_service.get_institution(
            session, institution_id
        )
        if inst:
            resolved_acronym = inst.get('acronym')

    if not resolved_acronym:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Acrônimo ou ID da instituição não informado',
        )

    path = get_institution_cover_path(resolved_acronym)
    if not path or not path.exists():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Capa da instituição não encontrada',
        )

    return FileResponse(path)


@router.get('/institution/{institution_id}', response_model=Institution)
async def get_institution(session: AsyncSession, institution_id: UUID):
    institution = await researcher_service.get_institution(
        session, institution_id
    )
    if not institution:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Instituição não encontrada',
        )
    return institution
