from typing import Optional
from uuid import UUID

from sqlalchemy import (
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
class Labs:
    __tablename__ = 'labs'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    hashed_id: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(Text)
    researcher_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('researcher.id', ondelete='SET NULL'), default=None
    )
    location: Mapped[Optional[str]] = mapped_column(Text, default=None)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    website: Mapped[Optional[str]] = mapped_column(Text, default=None)
    activities: Mapped[Optional[str]] = mapped_column(Text, default=None)
    areas: Mapped[Optional[str]] = mapped_column(Text, default=None)
    campus: Mapped[Optional[str]] = mapped_column(Text, default=None)
    institution_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('institution.id'), default=None
    )
    responsible: Mapped[Optional[str]] = mapped_column(Text, default=None)


@table_registry.mapped_as_dataclass
class Sdg:
    __tablename__ = 'sdg'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)


@table_registry.mapped_as_dataclass
class SdgAlignment:
    __tablename__ = 'sdg_alignment'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    reference_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    type: Mapped[str] = mapped_column(String)
    sdg_id: Mapped[UUID] = mapped_column(ForeignKey('sdg.id'))


@table_registry.mapped_as_dataclass
class ResearchDictionary:
    __tablename__ = 'research_dictionary'

    research_dictionary_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    term: Mapped[Optional[str]] = mapped_column(String, default=None)
    frequency: Mapped[Optional[int]] = mapped_column(Integer, default=1)
    type_: Mapped[Optional[str]] = mapped_column(String, default=None)
