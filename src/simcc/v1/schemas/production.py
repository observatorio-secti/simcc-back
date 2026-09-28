from typing import Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel

from simcc.v1.schemas.common import PaginationParams


class ArticleProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: Union[UUID, list[UUID]]
    researcher: Union[str, list[str]]
    researcher_id: Union[UUID, list[UUID]]
    lattes_id: Union[str, list[str]]
    lattes_10_id: Union[str, list[str]]
    authors: Optional[str]

    # Dados Básicos
    title: str
    year: Optional[int]
    type: str
    language: Optional[str]
    abstract: Optional[str]
    keywords: Optional[str]

    # Dados Específicos
    doi: Optional[str]
    qualis: Literal['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4', 'C', 'SQ']
    magazine: str
    jif: Optional[str]
    jcr_link: Optional[str]
    article_institution: Optional[str]
    authors_institution: Optional[str]
    issn: Optional[str]
    landing_page_url: Optional[str]
    pdf: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0
    citations_count: Optional[Union[int, str]]
    has_image: Optional[bool] = False
    relevance: Optional[bool] = False
    quadrennial: Optional[str] = None


class BookProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: Union[UUID, list[UUID]]
    researcher: Union[UUID, list[UUID]]
    lattes_id: Union[str, list[str]]
    name: Union[str, list[str]]

    # Dados Básicos
    title: str
    year: int

    # Dados Específicos
    isbn: Optional[str]
    publishing_company: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0
    has_image: Optional[bool] = False
    relevance: Optional[bool] = False


class BookChapterProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: Union[UUID, list[UUID]]
    researcher: Union[UUID, list[UUID]]
    lattes_id: Union[str, list[str]]
    name: Union[str, list[str]]

    # Dados Básicos
    title: str
    year: int

    # Dados Específicos
    isbn: Optional[str]
    publishing_company: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0
    has_image: Optional[bool] = False
    relevance: Optional[bool] = False


class PapersProduction(BaseModel):
    # Identificadores e Relacionamentos
    name: Union[str, list[str]]
    authors: Optional[Union[str, list]]

    # Dados Básicos
    title: str
    title_en: Optional[str]
    year_: int
    language: Optional[str]

    # Dados Específicos
    nature: str
    means_divulgation: str
    homepage: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0
    has_image: Optional[bool] = False
    relevance: Optional[bool] = False
    scientific_divulgation: Optional[bool]


class EventProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    researcher_id: UUID
    name: str
    lattes_id: Optional[str]
    lattes_10_id: Optional[str]
    authors: Optional[str]

    # Dados Básicos
    title: str
    title_en: Optional[str]
    nature: Optional[str]
    language: Optional[str]
    year_: int

    # Dados Específicos
    means_divulgation: Optional[str]
    homepage: Optional[str]
    scientific_divulgation: Optional[bool]
    event_classification: Optional[str]
    event_name: Optional[str]
    event_city: Optional[str]
    event_year: Optional[int]
    proceedings_title: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    series: Optional[str]
    start_page: Optional[str]
    end_page: Optional[str]
    publisher_name: Optional[str]
    publisher_city: Optional[str]
    event_name_english: Optional[str]
    identifier_number: Optional[str]
    isbn: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0
    relevance: Optional[bool] = False


class ResearchProjectProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    researcher_id: UUID
    name: str

    # Dados Básicos
    project_name: str
    start_year: Optional[int]
    end_year: Optional[int]
    status: Optional[str]
    nature: Optional[str]
    description: Optional[str]

    # Dados Específicos
    agency_code: Optional[str]
    agency_name: Optional[str]
    number_undergraduates: Optional[int]
    number_specialists: Optional[int]
    number_academic_masters: Optional[int]
    number_phd: Optional[int]
    production: Optional[list]
    foment: Optional[list]
    components: Optional[list]

    # Métricas e Flags
    stars: Optional[int] = 0


class GuidanceProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    researcher_id: UUID
    name: str
    lattes_id: Optional[str]

    # Dados Básicos
    title: str
    year: int
    nature: Optional[str]
    oriented: Optional[str]
    type: Optional[str]
    status: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0


class ReportProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    name: str

    # Dados Básicos
    title: str
    year: int
    project_name: Optional[str]

    # Dados Específicos
    financing: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0


class SoftwareProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    researcher_id: UUID
    name: str
    lattes_id: Optional[str]

    # Dados Básicos
    title: str
    year: int

    # Dados Específicos
    platform: Optional[str]
    goal: Optional[str]
    environment: Optional[str]
    availability: Optional[str]
    financing_institutionc: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0
    has_image: Optional[bool] = False
    relevance: Optional[bool] = False


class BrandProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    researcher_id: UUID
    name: str
    lattes_id: Optional[str]

    # Dados Básicos
    title: str
    year: int

    # Dados Específicos
    goal: Optional[str]
    nature: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0
    has_image: Optional[bool] = False
    relevance: Optional[bool] = False


class ParticipationEventProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    name: str

    # Dados Básicos
    title: str
    event_name: Optional[str]
    nature: Optional[str]
    form_participation: Optional[str]
    year: int


class ProfessionalExperience(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    researcher_id: UUID
    researcher_name: str
    lattes_id: Optional[str]

    # Dados Básicos
    enterprise: str
    start_year: int
    end_year: Optional[int]
    graduation: Optional[str]

    # Dados Específicos
    employment_type: Optional[str]
    other_employment_type: Optional[str]
    functional_classification: Optional[str]
    other_functional_classification: Optional[str]
    workload_hours_weekly: Optional[int]
    exclusive_dedication: Optional[bool]
    additional_info: Optional[str]


class PatentProduction(BaseModel):
    # Identificadores e Relacionamentos
    id: UUID
    researcher: UUID
    name: str
    lattes_id: Optional[str]

    # Dados Básicos
    title: str
    year: int
    category: Optional[str]

    # Dados Específicos
    details: Optional[str]
    grant_date: Optional[str]
    deposit_date: Optional[str]
    code: Optional[str]

    # Métricas e Flags
    stars: Optional[int] = 0
    has_image: Optional[bool] = False
    relevance: Optional[bool] = False


class GraduateProgramProduction(BaseModel):
    id: Optional[UUID] = None
    article: int = 0
    book: int = 0
    book_chapter: int = 0
    work_in_event: int = 0
    patent: int = 0
    software: int = 0
    brand: int = 0
    doctors: int = 0
    masters: int = 0
    graduate: int = 0
    specialization: int = 0
    pos_doctors: int = 0
    researcher: int = 0


class GeneralProductionMetrics(BaseModel):
    year: int
    count_guidance: int = 0
    count_guidance_complete: int = 0
    count_guidance_in_progress: int = 0
    count_book: int = 0
    count_book_chapter: int = 0
    count_not_granted_patent: int = 0
    count_granted_patent: int = 0
    count_total: int = 0
    count_software: int = 0
    count_report: int = 0
    count_article: int = 0
    count_patent: int = 0
    count_brand: int = 0
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


class RecentlyUpdatedArticle(BaseModel):
    researcher_id: UUID
    article_institution: Optional[str] = None
    issn: Optional[Union[str, list]] = None
    authors_institution: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[str] = None
    language: Optional[str] = None
    citations_count: Optional[Union[int, str]] = 0
    pdf: Optional[str] = None
    landing_page_url: Optional[str] = None
    keywords: Optional[str] = None
    title: str
    year: str
    doi: Optional[str] = None
    qualis: Optional[str] = None
    name_periodical: Optional[str] = None
    researcher: str
    lattes_id: str
    jif: Optional[str] = None
    jcr_link: Optional[str] = None


class Magazine(BaseModel):
    id: UUID
    magazine: str
    issn: str
    jcr: Optional[Union[float, str]] = None
    jcr_link: Optional[str] = None
    qualis: Optional[str] = None


class MagazineFilters(PaginationParams, BaseModel):
    initials: Optional[str] = None
    issn: Optional[str] = None
