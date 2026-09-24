from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class ResearcherArticleProduction(BaseModel):
    name: str
    year: int
    a1: int = 0
    a2: int = 0
    a3: int = 0
    a4: int = 0
    b1: int = 0
    b2: int = 0
    b3: int = 0
    b4: int = 0
    c: int = 0
    sq: int = 0
    citations: int = 0


class Department(BaseModel):
    dep_id: str
    org_cod: Optional[str]
    dep_nom: Optional[str]
    dep_des: Optional[str]
    dep_email: Optional[str]
    dep_site: Optional[str]
    dep_sigla: Optional[str]
    dep_tel: Optional[str]
    researchers: List[str]


class Docente(BaseModel):
    researcher_id: UUID
    full_name: str
    gender: Optional[str]
    status_code: Optional[str]
    work_regime: Optional[str]
    job_class: Optional[str]
    job_title: Optional[str]
    job_rank: Optional[str]
    job_reference_code: Optional[str]
    academic_degree: Optional[str]
    organization_entry_date: Optional[date]
    last_promotion_date: Optional[date]
    employment_status_description: Optional[str]
    department_name: Optional[str]
    career_category: Optional[str]
    academic_unit: Optional[str]
    unit_code: Optional[str]
    function_code: Optional[str]
    position_code: Optional[str]
    leadership_start_date: Optional[date]
    leadership_end_date: Optional[date]
    current_function_name: Optional[str]
    function_location: Optional[str]
    registration_number: Optional[str]
    ufmg_registration_number: Optional[str]
    semester_reference: Optional[str]


class ResearcherData(BaseModel):
    nome: str
    cpf: str
    classe: Optional[int]
    nivel: Optional[int]
    inicio: Optional[datetime]
    fim: Optional[datetime]
    tempo_nivel: Optional[int]
    tempo_acumulado: Optional[int]
    arquivo: Optional[str]


class Technician(BaseModel):
    technician_id: UUID
    full_name: Optional[str]
    gender: Optional[str]
    status_code: Optional[str]
    work_regime: Optional[str]
    job_class: Optional[str]
    job_title: Optional[str]
    job_rank: Optional[str]
    job_reference_code: Optional[str]
    academic_degree: Optional[str]
    organization_entry_date: Optional[date]
    last_promotion_date: Optional[date]
    employment_status_description: Optional[str]
    department_name: Optional[str]
    career_category: Optional[str]
    academic_unit: Optional[str]
    unit_code: Optional[str]
    function_code: Optional[str]
    position_code: Optional[str]
    leadership_start_date: Optional[date]
    leadership_end_date: Optional[date]
    current_function_name: Optional[str]
    function_location: Optional[str]
    registration_number: Optional[str]
    ufmg_registration_number: Optional[str]
    semester_reference: Optional[str]


class Mandate(BaseModel):
    member: str
    departament: str
    mandate: Optional[str]
    email: Optional[str]
    phone: Optional[str]


class WordFrequency(BaseModel):
    word: str
    freq: int
