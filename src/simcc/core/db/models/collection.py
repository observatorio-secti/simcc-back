from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from simcc.core.db.models.base import table_registry


@table_registry.mapped_as_dataclass
class Collection:
    __tablename__ = 'collection'

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default=None)
    refresh_interval_days: Mapped[int] = mapped_column(Integer, default=1)
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text('false')
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text('now()'), init=False
    )


@table_registry.mapped_as_dataclass
class ResearcherCollection:
    __tablename__ = 'researcher_collection'
    __table_args__ = (
        UniqueConstraint(
            'researcher_id', 'collection_id', name='uq_researcher_collection'
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
        init=False,
    )
    researcher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('researcher.id', ondelete='CASCADE'),
        nullable=False,
    )
    collection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('collection.id', ondelete='CASCADE'),
        nullable=False,
    )
    attributes: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text('now()'), init=False
    )
