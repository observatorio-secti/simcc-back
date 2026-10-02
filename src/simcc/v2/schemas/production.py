"""Schemas V2 para produções científicas (Artigos e demais produções)."""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.researcher import Meta


class ResearcherRef(BaseModel):
    """Referência enxuta a um pesquisador cadastrado na plataforma."""

    id: UUID = Field(description='Identificador do pesquisador')
    name: str = Field(description='Nome do pesquisador')
    lattes_id: Optional[str] = Field(None, description='ID Lattes')


class MagazineRef(BaseModel):
    """Informações do periódico/revista onde o artigo foi publicado."""

    name: Optional[str] = Field(None, description='Nome da revista/periódico')
    issn: Optional[str] = Field(None, description='ISSN da publicação')
    qualis: Optional[str] = Field(None, description='Qualis CAPES')
    jcr: Optional[str] = Field(None, description='Fator de impacto JCR')


class ArticleRef(BaseModel):
    """Referência básica a um artigo científico."""

    id: UUID = Field(description='Identificador único canônico do artigo')
    title: str = Field(description='Título do artigo')
    year: Optional[int] = Field(None, description='Ano de publicação')
    doi: Optional[str] = Field(None, description='DOI do artigo')


MIN_VALID_YEAR = 1900
MAX_VALID_YEAR = 2100


class ArticleMatch(BaseModel):
    """Trecho destacado onde o termo de busca casou no artigo."""

    field: str = Field(
        description='Campo onde casou (title, abstract, keywords, magazine)'
    )
    snippet: str = Field(
        description='Trecho contendo os termos destacados em <b>...</b>'
    )


class ArticleSummary(ArticleRef):
    """Representação de artigo para listagens, buscas e cards no frontend."""

    magazine: Optional[MagazineRef] = None
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list,
        description='Coautores pesquisadores cadastrados na plataforma',
    )
    citations_count: int = Field(
        0, description='Total de citações registradas no OpenAlex'
    )
    has_abstract: bool = Field(
        False, description='Indica se o artigo possui resumo no OpenAlex'
    )
    has_open_access_pdf: bool = Field(
        False, description='Indica se possui link para PDF em acesso aberto'
    )
    matches: Optional[list[ArticleMatch]] = Field(
        None,
        description='Evidências de busca quando termo textual (q) pesquisado',
    )


class ArticleDetail(ArticleSummary):
    """Dossiê completo do artigo para página de detalhe."""

    abstract: Optional[str] = Field(
        None, description='Resumo completo do artigo (OpenAlex)'
    )
    landing_page_url: Optional[str] = Field(
        None, description='URL da página oficial da publicação'
    )
    pdf_url: Optional[str] = Field(
        None, description='URL direta do arquivo PDF em acesso aberto'
    )
    keywords: Optional[str] = Field(
        None, description='Palavras-chave registradas no OpenAlex'
    )
    all_authors_raw: Optional[str] = Field(
        None, description='Citação textual de todos os autores da publicação'
    )
    language: Optional[str] = Field(
        None, description='Idioma da publicação'
    )


class ArticleFilter(BaseModel):
    """Filtros para busca e listagem de artigos."""

    q: Optional[str] = Field(None, description='Termo para busca textual')
    year_start: Optional[int] = Field(
        None, description='Ano inicial de publicação'
    )
    year_end: Optional[int] = Field(
        None, description='Ano final de publicação'
    )
    qualis: list[str] = Field(
        default_factory=list,
        description='Classificação Qualis (ex: A1, A2, B1)',
    )
    researcher_id: list[UUID] = Field(
        default_factory=list,
        description='Filtrar por IDs de pesquisadores da plataforma',
    )
    institution_id: list[UUID] = Field(
        default_factory=list,
        description='Filtrar por IDs de instituições',
    )
    graduate_program_id: list[UUID] = Field(
        default_factory=list,
        description='Filtrar por IDs de programas de pós-graduação',
    )
    has_open_access: Optional[bool] = Field(
        None, description='Filtrar apenas artigos com PDF em acesso aberto'
    )

    @field_validator('year_start', 'year_end')
    @classmethod
    def _valid_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < MIN_VALID_YEAR or v > MAX_VALID_YEAR):
            raise ValueError('Ano deve estar entre 1900 e 2100')
        return v

    @model_validator(mode='after')
    def _validate_year_range(self) -> 'ArticleFilter':
        if (
            self.year_start is not None
            and self.year_end is not None
            and self.year_start > self.year_end
        ):
            raise ValueError('year_start não pode ser maior que year_end')
        return self


class ArticleSort(BaseModel):
    """Critério e direção de ordenação para artigos."""

    by: Literal['relevance', 'year', 'citations', 'title'] = Field(
        'relevance', description='Critério de ordenação'
    )
    order: Literal['asc', 'desc'] = Field(
        'desc', description='Direção da ordenação'
    )


class ArticleSearchResponse(BaseModel):
    """Resposta paginada da busca de artigos científicos."""

    data: list[ArticleSummary] = Field(description='Lista paginada de artigos')
    pagination: Pagination = Field(description='Metadados de paginação')
    filters_applied: ArticleFilter = Field(
        description='Filtros aplicados na busca'
    )
    sort: ArticleSort = Field(description='Critério e direção de ordenação')
    meta: Meta = Field(description='Metadados de performance e cache')
