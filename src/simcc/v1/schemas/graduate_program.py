import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class GraduateProgram(BaseModel):
    graduate_program_id: UUID
    code: Optional[str] = None
    name: str
    name_en: Optional[str] = None
    basic_area: Optional[str] = None
    cooperation_project: Optional[bool] = None
    area: Optional[str] = None
    modality: Optional[str] = None
    type: Optional[str] = None
    rating: Optional[str] = None
    institution_id: Optional[UUID] = None
    state: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    url_image: Optional[str] = None
    acronym: Optional[str] = None
    description: Optional[str] = None
    visible: Optional[bool] = None
    site: Optional[str] = None
    coordinator: Optional[str] = None
    email: Optional[str] = None
    start: Optional[str] = None
    phone: Optional[str] = None
    periodicity: Optional[str] = None
    qtd_permanente: int = 0
    qtd_colaborador: int = 0
    qtd_estudantes: int = 0
    institution: Optional[str] = None
    researchers: List[str] = []

    @field_validator('cooperation_project', mode='before')
    @classmethod
    def validate_cooperation(cls, v: Any) -> Optional[bool]:
        if isinstance(v, str):
            v = v.strip()
            if v == 'Presente':
                return True
            if v == 'Nenhum':
                return False
        if isinstance(v, bool):
            return v
        return None

    @field_validator('start', mode='before')
    @classmethod
    def validate_start(cls, v: Any) -> Optional[str]:
        if isinstance(v, (datetime.date, datetime.datetime)):
            return v.strftime('%Y-%m-%d')
        return str(v) if v is not None else None


class ResearchLine(BaseModel):
    graduate_program_id: UUID
    name: str
    area: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class GraduateProgramResearcher(BaseModel):
    researcher_id: UUID
    name: str
    graduate_program_id: UUID
    type: str
    year: Optional[int] = None
