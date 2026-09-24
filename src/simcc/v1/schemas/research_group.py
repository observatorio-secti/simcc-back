from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ResearchGroup(BaseModel):
    id: UUID
    name: str
    institution: str
    first_leader: Optional[str] = None
    first_leader_id: Optional[UUID] = None
    second_leader: Optional[str] = None
    second_leader_id: Optional[UUID] = None
    area: Optional[str] = None
    census: Optional[str] = None
    start_of_collection: Optional[str] = None
    end_of_collection: Optional[str] = None
    group_identifier: Optional[str] = None
    year: Optional[int] = None
    institution_name: Optional[str] = None
    category: Optional[str] = None


class ResearchLine(BaseModel):
    line: str
    objective: Optional[str] = None
    keywords: Optional[str] = None
    major_area: Optional[str] = None
    area: Optional[str] = None
    year: Optional[int] = None


class ResearchGroupAreaCount(BaseModel):
    area: Optional[str] = None
    count: int
