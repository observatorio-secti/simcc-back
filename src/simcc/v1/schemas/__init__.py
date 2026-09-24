from enum import Enum
from typing import Optional, Union
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel

from simcc.v1.schemas.common import PaginationParams


class QualisOptions(str, Enum):
    A1: str = 'A1'
    A2: str = 'A2'
    A3: str = 'A3'
    A4: str = 'A4'
    B1: str = 'B1'
    B2: str = 'B2'
    B3: str = 'B3'
    B4: str = 'B4'
    C: str = 'C'
    SQ: str = 'SQ'


class DefaultFilters(PaginationParams, BaseModel):
    model_config = {'populate_by_name': True}

    # Identificadores e Relacionamentos
    institution_id: Optional[Union[UUID, str]] = None
    graduate_program_id: Optional[Union[UUID, str]] = None
    researcher_id: Optional[Union[UUID, str]] = None
    researcher_ids: Optional[list[Union[UUID, str]]] = None
    dep_id: Optional[str] = None
    group_id: Optional[Union[UUID, str]] = None
    collection_id: Optional[Union[UUID, str]] = None
    lattes_id: Optional[str] = None

    # Termos de Busca
    term: Optional[str] = Query(None, alias='term')
    terms: Optional[str] = Query(None, alias='terms')

    # Atributos e Localização
    institution: Optional[str] = Query(None, alias='university')
    university: Optional[str] = Query(None, include_in_schema=False)
    graduate_program: Optional[str] = None
    departament: Optional[str] = None
    group: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    modality: Optional[str] = None
    graduation: Optional[str] = None

    # Parâmetros de Consulta
    year: Optional[Union[int, str]] = None
    type: Optional[str] = None
    distinct: Optional[Union[int, str]] = 1

    # Métricas e Flags (deprecated)
    star: Optional[bool] = False
    has_image: Optional[bool] = False
    relevance: Optional[bool] = False
