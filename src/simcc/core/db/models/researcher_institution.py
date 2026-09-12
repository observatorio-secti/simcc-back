from typing import Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from simcc.core.db.models.base import table_registry


@table_registry.mapped_as_dataclass
class ResearcherInstitution:
    __tablename__ = 'researcher_institution'
    __table_args__ = (
        CheckConstraint(
            'workload >= 0 AND workload <= 168',
            name='ck_researcher_institution_workload',
        ),
    )

    researcher_id: Mapped[UUID] = mapped_column(
        ForeignKey('researcher.id', ondelete='CASCADE'), primary_key=True
    )
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey('institution.id', ondelete='CASCADE'), primary_key=True
    )
    identity_territory: Mapped[Optional[str]] = mapped_column(
        String, default=None
    )
    workload: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2, asdecimal=False), default=None
    )
    city_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey('city.id', ondelete='SET NULL'), default=None
    )
