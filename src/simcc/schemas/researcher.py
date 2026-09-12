from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel


class AcademicDegree(BaseModel):
    graduation: str
    among: int


class GreatArea(BaseModel):
    great_area: str
    count: int


class Lab(BaseModel):
    id: int
    hashed_id: str
    type: str
    location: str
    name: str
    description: str
    website: str
    activities: str
    areas: str
    campus: str
    institution_id: UUID
    researcher_id: UUID
    responsible: str


class YearlyMetric(BaseModel):
    year: int
    among: int


class QualisMetric(BaseModel):
    A1: int = 0
    A2: int = 0
    A3: int = 0
    A4: int = 0
    B1: int = 0
    B2: int = 0
    B3: int = 0
    B4: int = 0
    C: int = 0
    SQ: int = 0


class JCRMetric(BaseModel):
    very_low: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    not_applicable: int = 0
    without_jcr: int = 0


class ArticleMetric(BaseModel):
    year: int
    citations: int
    qualis: QualisMetric
    jcr: JCRMetric
    among: int
    count_doi: int


class PatentMetric(BaseModel):
    year: int
    not_granted: int
    granted: int


class GuidanceMetric(BaseModel):
    year: int
    m_completed: int = 0
    m_in_progress: int = 0
    ic_completed: int = 0
    ic_in_progress: int = 0
    d_completed: int = 0
    d_in_progress: int = 0
    g_completed: int = 0
    g_in_progress: int = 0
    e_completed: int = 0
    e_in_progress: int = 0
    sd_completed: int = 0
    sd_in_progress: int = 0


class SpeakerMetric(BaseModel):
    year: int
    congress: int
    meeting: int
    workshop: int
    other: int
    seminar: int
    symposium: int


class EducationMetric(BaseModel):
    year: int
    among: int
    degree: str


class ResearchProjectMetric(BaseModel):
    year: int
    nature: dict[str, int]
    among: int


class ResearcherCountMetric(BaseModel):
    researcher_count: int
    orcid_count: int
    scopus_count: int
    among: int


class LattesUpdateMetric(BaseModel):
    total: int
    over_3_months: int
    over_6_months: int


class ScholarshipMetric(BaseModel):
    modality_code: Optional[str] = None
    category_level_code: Optional[str] = None
    count: int


class ResearcherInstitution(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None
    acronym: Optional[str] = None
    image: Optional[str] = None
    cover: Optional[str] = None
    territorio_identidade: Optional[str] = None
    carga_horaria: Optional[float] = None


class Researcher(BaseModel):
    id: UUID
    institution_id: Optional[UUID] = None
    lattes_id: Optional[str]
    lattes_10_id: Optional[str]
    orcid: Optional[str] = None
    scopus: Optional[str] = None
    openalex: Optional[str] = None

    name: str
    university: Optional[str] = None
    graduation: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    image_university: Optional[str] = None

    abstract: Optional[str] = None
    abstract_ai: Optional[str] = None
    gender: Optional[str] = None
    classification: Optional[str] = None
    status: Optional[bool] = True
    lattes_update: Optional[datetime] = None

    # Colunas enriquecidas
    institution: Optional[ResearcherInstitution] = None
    research_groups: Optional[Union[list, str]] = []
    subsidy: Optional[Union[list, str]] = []
    departments: Optional[Union[list, str]] = []
    graduate_programs: Optional[Union[list, str]] = []
    ufmg: Optional[Any] = None
    user: Optional[Union[dict, str]] = {}
    custom_attributes: Optional[dict[str, Any]] = None

    among: Union[int, str] = 0
    articles: Union[int, str] = 0
    book_chapters: Union[int, str] = 0
    book: Union[int, str] = 0
    patent: Union[int, str] = 0
    software: Union[int, str] = 0
    brand: Union[int, str] = 0
    h_index: Union[int, str] = 0
    relevance_score: Union[int, str] = 0
    works_count: Union[int, str] = 0
    cited_by_count: Union[int, str] = 0
    i10_index: Union[int, str] = 0

    class Config:
        json_encoders = {datetime: lambda v: v.strftime('%d/%m/%Y')}


class CoAuthorship(BaseModel):
    name: str
    type: str
    among: int
    initials: str


class ResearcherScholarship(BaseModel):
    researcher_id: UUID
    name: str
    modality_code: Optional[str] = None
    modality_name: Optional[str] = None
    call_title: Optional[str] = None
    category_level_code: Optional[str] = None
    funding_program_name: Optional[str] = None
    institute_name: Optional[str] = None
    aid_quantity: Optional[int] = 0
    scholarship_quantity: Optional[int] = 0


class ResearcherTerm(BaseModel):
    among: int
    term: str


class OriginalWord(BaseModel):
    term: str
    frequency: str
    type: str
    checkbox: int = 0
