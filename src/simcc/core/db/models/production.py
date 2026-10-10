from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from simcc.core.db.models.base import table_registry


@table_registry.mapped_as_dataclass
class BibliographicProduction:
    __tablename__ = 'bibliographic_production'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('country.id'), default=None
    )
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    means_divulgation: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    relevance: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    has_image: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    scientific_divulgation: Mapped[Optional[bool]] = mapped_column(
        Boolean, default=False
    )
    authors: Mapped[Optional[str]] = mapped_column(String, default=None)
    year_: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_new: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)


@table_registry.mapped_as_dataclass
class BibliographicProductionArticle:
    __tablename__ = 'bibliographic_production_article'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    bibliographic_production_id: Mapped[UUID] = mapped_column(
        ForeignKey('bibliographic_production.id'),
        unique=True,
    )
    periodical_magazine_id: Mapped[UUID] = mapped_column(
        ForeignKey('periodical_magazine.id')
    )
    volume: Mapped[Optional[str]] = mapped_column(String, default=None)
    fascicle: Mapped[Optional[str]] = mapped_column(String, default=None)
    series: Mapped[Optional[str]] = mapped_column(String, default=None)
    start_page: Mapped[Optional[str]] = mapped_column(String, default=None)
    end_page: Mapped[Optional[str]] = mapped_column(String, default=None)
    place_publication: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    periodical_magazine_name: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    issn: Mapped[Optional[str]] = mapped_column(String, default=None)
    qualis: Mapped[Optional[str]] = mapped_column(String, default='SQ')
    jcr: Mapped[Optional[str]] = mapped_column(String, default=None)
    jcr_link: Mapped[Optional[str]] = mapped_column(String, default=None)
    stars: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    quadrennial: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class BibliographicProductionBook:
    __tablename__ = 'bibliographic_production_book'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    bibliographic_production_id: Mapped[UUID] = mapped_column(
        ForeignKey('bibliographic_production.id'),
        unique=True,
    )
    isbn: Mapped[Optional[str]] = mapped_column(String, default=None)
    qtt_volume: Mapped[Optional[str]] = mapped_column(String, default=None)
    qtt_pages: Mapped[Optional[str]] = mapped_column(String, default=None)
    num_edition_revision: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    num_series: Mapped[Optional[str]] = mapped_column(String, default=None)
    publishing_company: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    publishing_company_city: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    stars: Mapped[Optional[int]] = mapped_column(Integer, default=0)


@table_registry.mapped_as_dataclass
class BibliographicProductionBookChapter:
    __tablename__ = 'bibliographic_production_book_chapter'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    bibliographic_production_id: Mapped[UUID] = mapped_column(
        ForeignKey('bibliographic_production.id'),
        unique=True,
    )
    book_title: Mapped[Optional[str]] = mapped_column(String, default=None)
    isbn: Mapped[Optional[str]] = mapped_column(String, default=None)
    start_page: Mapped[Optional[str]] = mapped_column(String, default=None)
    end_page: Mapped[Optional[str]] = mapped_column(String, default=None)
    qtt_volume: Mapped[Optional[str]] = mapped_column(String, default=None)
    organizers: Mapped[Optional[str]] = mapped_column(String, default=None)
    num_edition_revision: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    num_series: Mapped[Optional[str]] = mapped_column(String, default=None)
    publishing_company: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    publishing_company_city: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    stars: Mapped[Optional[int]] = mapped_column(Integer, default=0)


@table_registry.mapped_as_dataclass
class Software:
    __tablename__ = 'software'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String, default=None)
    platform: Mapped[Optional[str]] = mapped_column(String, default=None)
    goal: Mapped[Optional[str]] = mapped_column(String, default=None)
    relevance: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    has_image: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    environment: Mapped[Optional[str]] = mapped_column(String, default=None)
    availability: Mapped[Optional[str]] = mapped_column(String, default=None)
    financing_institutionc: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_new: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text('true'), default=True
    )
    stars: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )
    code: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class Patent:
    __tablename__ = 'patent'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String, default=None)
    category: Mapped[Optional[str]] = mapped_column(String, default=None)
    relevance: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    has_image: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    development_year: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    details: Mapped[Optional[str]] = mapped_column(Text, default=None)
    code: Mapped[Optional[str]] = mapped_column(
        String, unique=False, default=None
    )
    grant_date: Mapped[Optional[datetime]] = mapped_column(default=None)
    deposit_date: Mapped[Optional[str]] = mapped_column(String, default=None)
    is_new: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text('true'), default=True
    )
    stars: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )


@table_registry.mapped_as_dataclass
class ResearchReport:
    __tablename__ = 'research_report'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String, default=None)
    project_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    financing_institutionc: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_new: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text('true'), default=True
    )
    stars: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )


@table_registry.mapped_as_dataclass
class Brand:
    __tablename__ = 'brand'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String, default=None)
    relevance: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    has_image: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    goal: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_new: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text('true'), default=True
    )
    stars: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )


@table_registry.mapped_as_dataclass
class AdvisoryActivity:
    __tablename__ = 'advisory_activity'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    organ_name: Mapped[Optional[str]] = mapped_column(String)
    start_year: Mapped[Optional[str]] = mapped_column(String)
    sequence_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    organ_code: Mapped[Optional[str]] = mapped_column(String, default=None)
    unit_code: Mapped[Optional[str]] = mapped_column(String, default=None)
    unit_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    specification: Mapped[Optional[str]] = mapped_column(Text, default=None)
    is_current: Mapped[Optional[str]] = mapped_column(String, default=None)
    start_month: Mapped[Optional[str]] = mapped_column(String, default=None)
    end_month: Mapped[Optional[str]] = mapped_column(String, default=None)
    end_year: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class ArtisticProduction:
    __tablename__ = 'artistic_production'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    title: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    sequence_code: Mapped[int] = mapped_column(Integer)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)


@table_registry.mapped_as_dataclass
class DidacticMaterial:
    __tablename__ = 'didactic_material'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    title: Mapped[str] = mapped_column(Text)
    sequence_code: Mapped[int] = mapped_column(Integer)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)


@table_registry.mapped_as_dataclass
class EventOrganization:
    __tablename__ = 'event_organization'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String, default=None)
    promoter_institution: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    local: Mapped[Optional[str]] = mapped_column(String, default=None)
    duration_in_weeks: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_new: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text('true'), default=True
    )


@table_registry.mapped_as_dataclass
class ResearchProject:
    __tablename__ = 'research_project'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    start_year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    end_year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    agency_code: Mapped[Optional[str]] = mapped_column(String, default=None)
    agency_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    project_name: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    number_undergraduates: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )
    number_specialists: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )
    number_academic_masters: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )
    number_phd: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    stars: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )


@table_registry.mapped_as_dataclass
class ResearchProjectComponents:
    __tablename__ = 'research_project_components'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    project_id: Mapped[UUID] = mapped_column(ForeignKey('research_project.id'))
    name: Mapped[Optional[str]] = mapped_column(String, default=None)
    lattes_id: Mapped[Optional[str]] = mapped_column(String, default=None)
    citations: Mapped[Optional[str]] = mapped_column(String, default=None)
    coordinator: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )


@table_registry.mapped_as_dataclass
class ResearchProjectFoment:
    __tablename__ = 'research_project_foment'

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey('research_project.id'), primary_key=True
    )
    agency_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    agency_code: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class ResearchProjectProduction:
    __tablename__ = 'research_project_production'

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey('research_project.id'), primary_key=True
    )
    title: Mapped[Optional[str]] = mapped_column(Text, default=None)
    type: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class TechnicalWorkProgram:
    __tablename__ = 'technical_work_program'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    title: Mapped[str] = mapped_column(Text)
    sequence_code: Mapped[int] = mapped_column(Integer)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    theme: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class TechnicalWork:
    __tablename__ = 'technical_work'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    title: Mapped[str] = mapped_column(Text)
    sequence_code: Mapped[int] = mapped_column(Integer)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    funding_institution: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    duration: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)


@table_registry.mapped_as_dataclass
class TechnicalWorkPresentation:
    __tablename__ = 'technical_work_presentation'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    title: Mapped[str] = mapped_column(Text)
    sequence_code: Mapped[int] = mapped_column(Integer)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    event_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    promoting_institution: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )


@table_registry.mapped_as_dataclass
class TechnologicalProduct:
    __tablename__ = 'technological_product'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    title: Mapped[str] = mapped_column(Text)
    sequence_code: Mapped[int] = mapped_column(Integer)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    type: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)


@table_registry.mapped_as_dataclass
class BibliographicProductionWorkInEvent:
    __tablename__ = 'bibliographic_production_work_in_event'

    bibliographic_production_id: Mapped[UUID] = mapped_column(
        ForeignKey('bibliographic_production.id'), primary_key=True
    )
    event_classification: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    event_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    event_city: Mapped[Optional[str]] = mapped_column(String, default=None)
    event_year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    proceedings_title: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    volume: Mapped[Optional[str]] = mapped_column(String, default=None)
    issue: Mapped[Optional[str]] = mapped_column(String, default=None)
    series: Mapped[Optional[str]] = mapped_column(String, default=None)
    start_page: Mapped[Optional[str]] = mapped_column(String, default=None)
    end_page: Mapped[Optional[str]] = mapped_column(String, default=None)
    publisher_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    publisher_city: Mapped[Optional[str]] = mapped_column(String, default=None)
    event_name_english: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    identifier_number: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    isbn: Mapped[Optional[str]] = mapped_column(String, default=None)
    stars: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )


@table_registry.mapped_as_dataclass
class ProcessOrTechnique:
    __tablename__ = 'process_or_technique'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    title: Mapped[str] = mapped_column(Text)
    sequence_code: Mapped[int] = mapped_column(Integer)
    sequence_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    title_en: Mapped[Optional[str]] = mapped_column(Text, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    home_page: Mapped[Optional[str]] = mapped_column(Text, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)
    is_relevant: Mapped[bool] = mapped_column(
        Boolean, server_default=text('false'), default=False
    )
    has_innovation_potential: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    purpose: Mapped[Optional[str]] = mapped_column(Text, default=None)
    purpose_en: Mapped[Optional[str]] = mapped_column(Text, default=None)
    availability: Mapped[Optional[str]] = mapped_column(String, default=None)
    funding_institution: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    city: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class Mockup:
    __tablename__ = 'mockup'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class Publishing:
    __tablename__ = 'publishing'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class IndustrialDesign:
    __tablename__ = 'industrial_design'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class MaintenanceArtisticWork:
    __tablename__ = 'maintenance_artistic_work'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class LetterMapOrSimilar:
    __tablename__ = 'letter_map_or_similar'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class ShortCourseTaught:
    __tablename__ = 'short_course_taught'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class RadioOrTvProgram:
    __tablename__ = 'radio_or_tv_program'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class ShortCourse:
    __tablename__ = 'short_course'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class SocialMediaWebsiteBlog:
    __tablename__ = 'social_media_website_blog'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class OtherTechnicalProduction:
    __tablename__ = 'other_technical_production'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    title: Mapped[str] = mapped_column(String)
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    production_sequence: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )
    title_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[str]] = mapped_column(String, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    language: Mapped[Optional[str]] = mapped_column(String, default=None)
    dissemination_medium: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    homepage: Mapped[Optional[str]] = mapped_column(String, default=None)
    doi: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class Guidance:
    __tablename__ = 'guidance'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    oriented: Mapped[Optional[str]] = mapped_column(String, default=None)
    type: Mapped[Optional[str]] = mapped_column(String, default=None)
    status: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_new: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text('true'), default=True
    )
    stars: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )


@table_registry.mapped_as_dataclass
class ParticipationEvents:
    __tablename__ = 'participation_events'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    title: Mapped[Optional[str]] = mapped_column(String, default=None)
    event_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    nature: Mapped[Optional[str]] = mapped_column(String, default=None)
    form_participation: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    type_participation: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    is_new: Mapped[Optional[bool]] = mapped_column(
        Boolean, server_default=text('true'), default=True
    )
    stars: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text('0'), default=0
    )


@table_registry.mapped_as_dataclass
class Foment:
    __tablename__ = 'foment'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    modality_code: Mapped[Optional[str]] = mapped_column(String, default=None)
    modality_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    call_title: Mapped[Optional[str]] = mapped_column(String, default=None)
    category_level_code: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    funding_program_name: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    institute_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    aid_quantity: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    scholarship_quantity: Mapped[Optional[int]] = mapped_column(
        Integer, default=None
    )


@table_registry.mapped_as_dataclass
class RegisteredCultivar:
    __tablename__ = 'registered_cultivar'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE')
    )
    sequence_code: Mapped[int] = mapped_column(Integer)
    denomination: Mapped[Optional[str]] = mapped_column(String, default=None)
    denomination_en: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    country: Mapped[Optional[str]] = mapped_column(String, default=None)
    code: Mapped[Optional[str]] = mapped_column(
        String, unique=True, default=None
    )


@table_registry.mapped_as_dataclass
class ProcessAuthor:
    __tablename__ = 'process_author'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    process_id: Mapped[UUID] = mapped_column(
        ForeignKey('process_or_technique.id')
    )
    full_name: Mapped[str] = mapped_column(String)
    citation_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    author_order: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    cnpq_id: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class ProcessKeyword:
    __tablename__ = 'process_keyword'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    process_id: Mapped[UUID] = mapped_column(
        ForeignKey('process_or_technique.id')
    )
    keyword: Mapped[str] = mapped_column(Text)
    order: Mapped[Optional[int]] = mapped_column(Integer, default=None)


@table_registry.mapped_as_dataclass
class ProcessKnowledgeArea:
    __tablename__ = 'process_knowledge_area'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    process_id: Mapped[UUID] = mapped_column(
        ForeignKey('process_or_technique.id')
    )
    major_area: Mapped[Optional[str]] = mapped_column(String, default=None)
    area_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    sub_area_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    specialty_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    order: Mapped[Optional[int]] = mapped_column(Integer, default=None)
