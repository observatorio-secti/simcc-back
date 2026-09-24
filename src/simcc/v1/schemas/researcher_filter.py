from pydantic import BaseModel


class ResearcherFilter(BaseModel):
    area: list[str]
    graduation: list[str]
    city: list[str]
    institution: list[str]
    modality: list[str]
    graduate_program: list[str]
    departament: list[str]
