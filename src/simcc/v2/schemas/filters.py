from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class BaseFilter(BaseModel):
    q: Optional[str] = None


class BaseTemporalFilter(BaseFilter):
    year_start: Optional[int] = None
    year_end: Optional[int] = None


class ResearcherFilter(BaseTemporalFilter):
    institution_id: Optional[UUID] = None
    graduate_program_id: Optional[UUID] = None


class ProductionFilter(BaseTemporalFilter):
    institution_id: Optional[UUID] = None
    graduate_program_id: Optional[UUID] = None
    researcher_id: Optional[UUID] = None
    type: Optional[str] = None
    qualis: Optional[str] = None
    magazine: Optional[str] = None


class InstitutionFilter(BaseFilter):
    institution_id: Optional[UUID] = None
    state: Optional[str] = None
    city: Optional[str] = None


class GraduateProgramFilter(BaseFilter):
    institution_id: Optional[UUID] = None
    area: Optional[str] = None
    modality: Optional[str] = None
    rating: Optional[str] = None
