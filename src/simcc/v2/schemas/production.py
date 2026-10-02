"""Schemas V2 para produções científicas (Artigos, Livros, etc.)."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.researcher import Meta

MIN_VALID_YEAR = 1900
MAX_VALID_YEAR = 2100


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


class ProductionBaseFilter(BaseModel):
    """Filtros base compartilhados entre produções."""

    q: Optional[str] = Field(None, description='Termo para busca textual')
    year_start: Optional[int] = Field(
        None, description='Ano inicial'
    )
    year_end: Optional[int] = Field(
        None, description='Ano final'
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

    @field_validator('year_start', 'year_end')
    @classmethod
    def _valid_year(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < MIN_VALID_YEAR or v > MAX_VALID_YEAR):
            raise ValueError('Ano deve estar entre 1900 e 2100')
        return v

    @model_validator(mode='after')
    def _validate_year_range(self) -> 'ProductionBaseFilter':
        if (
            self.year_start is not None
            and self.year_end is not None
            and self.year_start > self.year_end
        ):
            raise ValueError('year_start não pode ser maior que year_end')
        return self


class ArticleFilter(ProductionBaseFilter):
    """Filtros para busca e listagem de artigos."""

    qualis: list[str] = Field(
        default_factory=list,
        description='Classificação Qualis (ex: A1, A2, B1)',
    )
    has_open_access: Optional[bool] = Field(
        None, description='Filtrar apenas artigos com PDF em acesso aberto'
    )


class ArticleSort(BaseModel):
    """Critério e direção de ordenação para artigos."""

    by: Literal['relevance', 'year', 'citations', 'title'] = Field(
        'relevance', description='Critério de ordenação'
    )
    order: Literal['asc', 'desc'] = Field(
        'desc', description='Direção da ordenação'
    )


class ProductionSort(BaseModel):
    """Critério e direção de ordenação padrão para produções."""

    by: Literal['relevance', 'year', 'title'] = Field(
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


# =========================================================================
# 1. LIVROS
# =========================================================================

class BookSummary(BaseModel):
    """Card resumido de livro."""

    id: UUID = Field(description='ID canônico do livro')
    title: str = Field(description='Título do livro')
    year: Optional[int] = Field(None, description='Ano de publicação')
    isbn: Optional[str] = Field(None, description='ISBN')
    publishing_company: Optional[str] = Field(None, description='Editora')
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Autores da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class BookDetail(BookSummary):
    """Dossiê detalhado de livro."""

    doi: Optional[str] = Field(None, description='DOI')
    publishing_company_city: Optional[str] = Field(None, description='Cidade')
    all_authors_raw: Optional[str] = Field(None, description='Autores brutos')


class BookFilter(ProductionBaseFilter):
    """Filtros para busca de livros."""


class BookSearchResponse(BaseModel):
    """Resposta paginada da busca de livros."""

    data: list[BookSummary]
    pagination: Pagination
    filters_applied: BookFilter
    sort: ProductionSort
    meta: Meta


# =========================================================================
# 2. CAPÍTULOS DE LIVROS
# =========================================================================

class BookChapterSummary(BaseModel):
    """Card resumido de capítulo de livro."""

    id: UUID = Field(description='ID canônico do capítulo')
    title: str = Field(description='Título do capítulo')
    book_title: Optional[str] = Field(None, description='Título do livro')
    year: Optional[int] = Field(None, description='Ano de publicação')
    isbn: Optional[str] = Field(None, description='ISBN')
    publishing_company: Optional[str] = Field(None, description='Editora')
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Autores da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class BookChapterDetail(BookChapterSummary):
    """Dossiê detalhado de capítulo de livro."""

    doi: Optional[str] = Field(None, description='DOI')
    organizers: Optional[str] = Field(None, description='Organizadores')
    start_page: Optional[str] = Field(None, description='Página inicial')
    end_page: Optional[str] = Field(None, description='Página final')
    all_authors_raw: Optional[str] = Field(None, description='Autores brutos')


class BookChapterFilter(ProductionBaseFilter):
    """Filtros para busca de capítulos de livros."""


class BookChapterSearchResponse(BaseModel):
    """Resposta paginada da busca de capítulos."""

    data: list[BookChapterSummary]
    pagination: Pagination
    filters_applied: BookChapterFilter
    sort: ProductionSort
    meta: Meta


# =========================================================================
# 3. SOFTWARES
# =========================================================================

class SoftwareSummary(BaseModel):
    """Card resumido de software."""

    id: UUID = Field(description='ID canônico do software')
    title: str = Field(description='Título do software')
    year: Optional[int] = Field(None, description='Ano de desenvolvimento')
    platform: Optional[str] = Field(None, description='Plataforma')
    environment: Optional[str] = Field(None, description='Ambiente')
    code: Optional[str] = Field(None, description='Código do registro')
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Desenvolvedores da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class SoftwareDetail(SoftwareSummary):
    """Dossiê detalhado de software."""

    availability: Optional[str] = Field(None, description='Disponibilidade')
    financing: Optional[str] = Field(None, description='Financiamento')


class SoftwareFilter(ProductionBaseFilter):
    """Filtros para busca de softwares."""


class SoftwareSearchResponse(BaseModel):
    """Resposta paginada da busca de softwares."""

    data: list[SoftwareSummary]
    pagination: Pagination
    filters_applied: SoftwareFilter
    sort: ProductionSort
    meta: Meta


# =========================================================================
# 4. PATENTES
# =========================================================================

class PatentSummary(BaseModel):
    """Card resumido de patente."""

    id: UUID = Field(description='ID canônico da patente')
    title: str = Field(description='Título da patente')
    year: Optional[int] = Field(None, description='Ano')
    category: Optional[str] = Field(None, description='Categoria')
    code: Optional[str] = Field(
        None, description='Número do registro/depósito'
    )
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Inventores da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class PatentDetail(PatentSummary):
    """Dossiê detalhado de patente."""

    grant_date: Optional[datetime] = Field(None, description='Data concessão')
    deposit_date: Optional[str] = Field(None, description='Data depósito')
    details: Optional[str] = Field(None, description='Detalhes')


class PatentFilter(ProductionBaseFilter):
    """Filtros para busca de patentes."""


class PatentSearchResponse(BaseModel):
    """Resposta paginada da busca de patentes."""

    data: list[PatentSummary]
    pagination: Pagination
    filters_applied: PatentFilter
    sort: ProductionSort
    meta: Meta


# =========================================================================
# 5. PARTICIPAÇÃO EM EVENTOS
# =========================================================================

class EventSummary(BaseModel):
    """Card resumido de participação em evento."""

    id: UUID = Field(description='ID canônico da participação')
    title: str = Field(description='Título do trabalho ou apresentação')
    event_name: Optional[str] = Field(None, description='Nome do evento')
    year: Optional[int] = Field(None, description='Ano do evento')
    nature: Optional[str] = Field(None, description='Natureza do evento')
    type_participation: Optional[str] = Field(
        None, description='Tipo de participação'
    )
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Participantes da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class EventDetail(EventSummary):
    """Dossiê detalhado de participação em evento."""

    form_participation: Optional[str] = Field(
        None, description='Forma de participação'
    )


class EventFilter(ProductionBaseFilter):
    """Filtros para busca de participação em eventos."""


class EventSearchResponse(BaseModel):
    """Resposta paginada da busca de eventos."""

    data: list[EventSummary]
    pagination: Pagination
    filters_applied: EventFilter
    sort: ProductionSort
    meta: Meta
