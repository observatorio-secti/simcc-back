from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from simcc.core.db.models.base import table_registry


@table_registry.mapped_as_dataclass
class GraduateProgram:
    __tablename__ = 'graduate_program'

    graduate_program_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    name: Mapped[str] = mapped_column(String)
    area: Mapped[str] = mapped_column(String)
    modality: Mapped[str] = mapped_column(String)
    institution_id: Mapped[UUID] = mapped_column(ForeignKey('institution.id'))
    code: Mapped[Optional[str]] = mapped_column(String, default=None)
    name_en: Mapped[Optional[str]] = mapped_column(String, default=None)
    basic_area: Mapped[Optional[str]] = mapped_column(String, default=None)
    cooperation_project: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    type: Mapped[Optional[str]] = mapped_column(String, default=None)
    rating: Mapped[Optional[str]] = mapped_column(String, default=None)
    state: Mapped[Optional[str]] = mapped_column(String, default='BA')
    city: Mapped[Optional[str]] = mapped_column(String, default='Salvador')
    region: Mapped[Optional[str]] = mapped_column(String, default='Nordeste')
    url_image: Mapped[Optional[str]] = mapped_column(String, default=None)
    acronym: Mapped[Optional[str]] = mapped_column(String, default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    visible: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    site: Mapped[Optional[str]] = mapped_column(Text, default=None)
    coordinator: Mapped[Optional[str]] = mapped_column(String, default=None)
    email: Mapped[Optional[str]] = mapped_column(String, default=None)
    start: Mapped[Optional[date]] = mapped_column(Date, default=None)
    phone: Mapped[Optional[str]] = mapped_column(String, default=None)
    periodicity: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class GraduateProgramResearcher:
    __tablename__ = 'graduate_program_researcher'
    __table_args__ = (
        UniqueConstraint(
            'graduate_program_id',
            'researcher_id',
            'year',
            name='uq_graduate_program_researcher_program_researcher_year',
        ),
    )

    graduate_program_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            'graduate_program.graduate_program_id',
            onupdate='CASCADE',
            ondelete='CASCADE',
        ),
        primary_key=True,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', onupdate='CASCADE', ondelete='CASCADE'),
        primary_key=True,
    )
    type_: Mapped[Optional[str]] = mapped_column(String, default=None)
    year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    tag: Mapped[Optional[str]] = mapped_column(String, default=None)


@table_registry.mapped_as_dataclass
class GraduateProgramStudent:
    __tablename__ = 'graduate_program_student'

    graduate_program_id: Mapped[UUID] = mapped_column(
        ForeignKey('graduate_program.graduate_program_id'), primary_key=True
    )
    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE'), primary_key=True
    )
    year: Mapped[list[int]] = mapped_column(ARRAY(Integer), primary_key=True)


@table_registry.mapped_as_dataclass
class ResearchLinesPrograms:
    __tablename__ = 'research_lines_programs'

    graduate_program_id: Mapped[UUID] = mapped_column(
        ForeignKey('graduate_program.graduate_program_id'), primary_key=True
    )
    name: Mapped[str] = mapped_column(Text, primary_key=True)
    area: Mapped[str] = mapped_column(String)
    start_year: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    end_year: Mapped[Optional[int]] = mapped_column(Integer, default=None)


@table_registry.mapped_as_dataclass
class GraduateProgramIndProd:
    __tablename__ = 'graduate_program_ind_prod'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    graduate_program_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    year: Mapped[int] = mapped_column(Integer)
    ind_prod_article: Mapped[Optional[float]] = mapped_column(
        Float, default=None
    )
    ind_prod_book: Mapped[Optional[float]] = mapped_column(Float, default=None)
    ind_prod_book_chapter: Mapped[Optional[float]] = mapped_column(
        Float, default=None
    )
    ind_prod_software: Mapped[Optional[float]] = mapped_column(
        Float, default=None
    )
    ind_prod_report: Mapped[Optional[float]] = mapped_column(
        Float, default=None
    )
    ind_prod_granted_patent: Mapped[Optional[float]] = mapped_column(
        Float, default=None
    )
    ind_prod_not_granted_patent: Mapped[Optional[float]] = mapped_column(
        Float, default=None
    )
    ind_prod_guidance: Mapped[Optional[float]] = mapped_column(
        Float, default=None
    )
