from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from zeep import Client

from simcc.core.dependencies import AsyncSession, Filters
from simcc.v1.schemas.external import (
    Department,
    Docente,
    ResearcherArticleProduction,
    ResearcherData,
    Technician,
    WordFrequency,
)
from simcc.v1.schemas.institution import RtMetrics
from simcc.v1.services import external_service

router = APIRouter(tags=['External Integration - UFMG/Conectee'])

CNPQ_WSDL_URL = 'http://servicosweb.cnpq.br/srvcurriculo/WSCurriculo?wsdl'


def get_cnpq_client():
    try:
        return Client(CNPQ_WSDL_URL)
    except Exception as e:
        raise HTTPException(
            status_code=503, detail='CNPq service is unavailable'
        ) from e


@router.get('/getIdentificadorCNPq')
def get_lattes_id(
    cpf: str | None = None,
    nomeCompleto: str | None = None,
    dataNascimento: str | None = None,
):  # pragma: no cover
    client = get_cnpq_client()
    try:
        response_content = client.service.getIdentificadorCNPq(
            cpf=cpf, nomeCompleto=nomeCompleto, dataNascimento=dataNascimento
        )
        if response_content:
            return PlainTextResponse(content=str(response_content))
        raise HTTPException(status_code=404, detail='Identifier not found')
    except Exception as e:
        raise HTTPException(
            status_code=500, detail='Error processing CNPq request'
        ) from e


@router.get(
    '/getCurriculoCompactado',
    response_class=FileResponse,
)
def get_lattes_xml(lattes_id: str):  # pragma: no cover
    client = get_cnpq_client()
    try:
        response = client.service.getCurriculoCompactado(lattes_id)
        if not response:
            raise HTTPException(status_code=404, detail='Curriculum not found')

        storage_path = Path('storage')
        storage_path.mkdir(exist_ok=True)

        file_path = storage_path / f'{lattes_id}.zip'
        file_path.write_bytes(response)

        return FileResponse(
            path=file_path,
            filename=f'{lattes_id}.zip',
            media_type='application/zip',
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail='Error retrieving curriculum file'
        ) from e


@router.get(
    '/getDataAtualizacaoCV',
    response_model=str,
)
def get_current_lattes_date(lattes_id: str):  # pragma: no cover
    client = get_cnpq_client()
    try:
        response = client.service.getDataAtualizacaoCV(lattes_id)
        if response:
            return datetime.strptime(response, '%d/%m/%Y %H:%M:%S').strftime(
                '%d/%m/%Y %H:%M:%S'
            )
        raise HTTPException(status_code=404, detail='Curriculum not found')
    except ValueError as e:
        raise HTTPException(
            status_code=500, detail='Error parsing date from service'
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail='Error processing date request'
        ) from e


@router.get(
    '/ufmg/departament/{dep_id}/article_production',
    response_model=List[ResearcherArticleProduction],
)
async def list_article_production(
    dep_id: str,
    session: AsyncSession,
    year: int = Query(2020),
    program_id: Optional[UUID] = Query(None),
):
    return await external_service.list_article_production(
        session, program_id, dep_id, year
    )


@router.get('/ufmg/departament', response_model=List[Department])
@router.get('/ufmg/departamentos', include_in_schema=False)
async def get_departament(
    session: AsyncSession, dep_id: Optional[str] = Query(None)
):
    return await external_service.get_departament(session, dep_id)


@router.get('/ufmg/docentes', response_model=List[Docente])
async def get_docentes(session: AsyncSession, filters: Filters):
    return await external_service.get_docentes(session, filters)


@router.get('/ufmg/researcher', response_model=List[ResearcherData])
async def get_researcher_data(
    session: AsyncSession,
    cpf: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
):
    return await external_service.get_researcher_data(session, cpf, name)


@router.get('/ufmg/technician', response_model=List[Technician])
async def get_technician(session: AsyncSession):
    return await external_service.get_technician(session)


@router.get('/ufmg/departament/rt', response_model=RtMetrics)
@router.get('/departament/rt', include_in_schema=False)
async def get_departament_rt(session: AsyncSession):
    return await external_service.get_departament_rt(session)


@router.get('/secondWord', response_model=List[WordFrequency])
async def list_words(session: AsyncSession, term: str = Query(...)):
    return await external_service.list_words(session, term)


@router.post('/ufmg/congregation')
async def post_congregation(
    session: AsyncSession, file: UploadFile = File(...)
):
    await external_service.post_congregation(session, file)
    return {'detail': 'Congregation mandates processed successfully'}
