from pydantic import BaseModel, Field


class ResearcherFilter(BaseModel):
    area: list[str]
    graduation: list[str]
    city: list[str]
    institution: list[str]
    modality: list[str]
    graduate_program: list[str]
    departament: list[str]
    identity_territory: list[str] = Field(default_factory=list)
