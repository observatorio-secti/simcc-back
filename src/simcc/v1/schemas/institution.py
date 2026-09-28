from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class Institution(BaseModel):
    id: UUID
    name: str
    acronym: str
    count_r: int
    count_gp: int
    count_gpr: int
    count_gps: int
    count_foment: int
    count_rg: int
    count_d: int
    count_t: int
    researchers: List[str]
    image: Optional[str] = None
    cover: Optional[str] = None


class WorkRegimeCount(BaseModel):
    rt: str
    count: int


class RtMetrics(BaseModel):
    teachers: List[WorkRegimeCount]
    technician: List[WorkRegimeCount]


class InstitutionMetric(BaseModel):
    id: UUID
    institution: str
    among: str
    image: Optional[str] = None
