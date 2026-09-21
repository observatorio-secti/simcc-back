from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    PROFILE = 'PROFILE'
    ARTICLE = 'ARTICLE'
    BOOK = 'BOOK'
    BOOK_CHAPTER = 'BOOK_CHAPTER'
    PATENT = 'PATENT'
    SOFTWARE = 'SOFTWARE'


class MatchField(str, Enum):
    NAME = 'name'
    ABSTRACT = 'abstract'
    TITLE = 'title'
    KEYWORDS = 'keywords'


class MatchType(str, Enum):
    FTS = 'fts'
    FUZZY = 'fuzzy'


class MatchedInItem(BaseModel):
    source_type: SourceType = Field(..., description='Origem do documento')
    source_id: Optional[UUID | str] = Field(
        None, description='Identificador único do documento'
    )
    field: MatchField = Field(..., description='Campo em que ocorreu o match')
    title: str = Field(..., description='Título do documento ou do perfil')
    snippet: Optional[str] = Field(
        None, description='Fragmento destacado com termos'
    )
    score: Optional[float] = Field(
        None, description='Relevância pontual do documento'
    )
    match_type: MatchType = Field(
        MatchType.FTS, description='Tipo de casamento (fts ou fuzzy)'
    )


class ResearcherV2(BaseModel):
    researcher_id: Optional[UUID | str] = Field(
        None, description='Identificador do pesquisador'
    )
    name: str = Field(..., description='Nome do pesquisador')
    relevance_score: Optional[float] = Field(
        None, description='Score de relevância geral'
    )
    matched_in: Optional[list[MatchedInItem]] = Field(
        default=None,
        description='Documentos granulares em que houve correspondência',
    )
