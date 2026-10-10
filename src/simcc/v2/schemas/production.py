"""Schemas V2 para produções científicas (Artigos, Livros, etc.)."""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.researcher import FacetResult, Meta

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
    city_id: list[UUID] = Field(
        default_factory=list,
        description='IDs das cidades de vínculo dos autores da plataforma',
    )
    identity_territory: list[str] = Field(
        default_factory=list,
        description=(
            'Territórios de identidade dos vínculos dos autores da plataforma'
        ),
    )
    area: list[str] = Field(
        default_factory=list,
        description='Grande Área do Conhecimento dos autores da plataforma',
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
    magazine_name: list[str] = Field(
        default_factory=list,
        description='Nome da revista/periódico',
    )
    issn: list[str] = Field(
        default_factory=list,
        description='ISSN do periódico',
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


COMMON_PRODUCTION_FACETS = (
    'institution',
    'graduate_program',
    'city',
    'identity_territory',
    'year',
    'area',
)


class ProductionOptions(BaseModel):
    """Opções opt-in das listagens de produção.

    Os facets aceitos variam por tipo de produção (ver
    `repositories/production_facets_repo.py`); a validação é feita no
    serviço, que conhece o endpoint.
    """

    facets: list[str] = Field(
        default=[],
        description=(
            'Lista de facets opt-in. Comuns: '
            f'{", ".join(COMMON_PRODUCTION_FACETS)}. Cada tipo de produção '
            'aceita também os facets dos seus filtros próprios'
        ),
    )
    facet_limit: int = Field(
        20,
        ge=1,
        le=100,
        description='Número máximo de valores por facet',
    )

    @field_validator('facets', mode='before')
    @classmethod
    def _split_comma_separated(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, (list, tuple, set)):
            return []
        return [
            part.strip()
            for item in v
            if isinstance(item, str)
            for part in item.split(',')
            if part.strip()
        ]


class ArticleSearchResponse(BaseModel):
    """Resposta paginada da busca de artigos científicos."""

    data: list[ArticleSummary] = Field(description='Lista paginada de artigos')
    pagination: Pagination = Field(description='Metadados de paginação')
    filters_applied: ArticleFilter = Field(
        description='Filtros aplicados na busca'
    )
    sort: ArticleSort = Field(description='Critério e direção de ordenação')
    meta: Meta = Field(description='Metadados de performance e cache')
    facets: Optional[dict[str, FacetResult]] = Field(
        None, description='Facets solicitados em `facets`'
    )


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
    facets: Optional[dict[str, FacetResult]] = None


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
    facets: Optional[dict[str, FacetResult]] = None


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
    facets: Optional[dict[str, FacetResult]] = None


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

    category: list[str] = Field(
        default_factory=list,
        description='Categoria da patente (ex.: Produto, Processo)',
    )
    granted: Optional[bool] = Field(
        None,
        description=(
            'Apenas patentes concedidas (true) ou ainda não concedidas '
            '(false)'
        ),
    )


class PatentSearchResponse(BaseModel):
    """Resposta paginada da busca de patentes."""

    data: list[PatentSummary]
    pagination: Pagination
    filters_applied: PatentFilter
    sort: ProductionSort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 5. PARTICIPAÇÃO EM EVENTOS
# =========================================================================

class EventSummary(BaseModel):
    """Card resumido de participação em evento."""

    id: UUID = Field(description='ID canônico da participação')
    title: Optional[str] = Field(
        None,
        description=(
            'Título do trabalho ou apresentação (ausente quando a '
            'participação não teve trabalho apresentado)'
        ),
    )
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

    nature: list[str] = Field(
        default_factory=list,
        description='Natureza do evento (ex.: Congresso, Seminário)',
    )
    type_participation: list[str] = Field(
        default_factory=list,
        description='Tipo de participação (ex.: Apresentação Oral)',
    )
    form_participation: list[str] = Field(
        default_factory=list,
        description='Forma de participação (ex.: Convidado, Ouvinte)',
    )


class EventSearchResponse(BaseModel):
    """Resposta paginada da busca de eventos."""

    data: list[EventSummary]
    pagination: Pagination
    filters_applied: EventFilter
    sort: ProductionSort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 6. PROJETOS DE PESQUISA
# =========================================================================

class ResearchProjectFoment(BaseModel):
    """Agência financiadora de um projeto de pesquisa."""

    agency_name: Optional[str] = Field(None, description='Nome da agência')
    agency_code: Optional[str] = Field(None, description='Código da agência')
    nature: Optional[str] = Field(
        None, description='Natureza do financiamento (ex.: Bolsa, Auxílio)'
    )


class ResearchProjectComponent(BaseModel):
    """Integrante de um projeto de pesquisa, conforme declarado no Lattes."""

    name: Optional[str] = Field(None, description='Nome do integrante')
    lattes_id: Optional[str] = Field(None, description='ID Lattes')
    citations: Optional[str] = Field(
        None, description='Nome em citações bibliográficas'
    )
    coordinator: bool = Field(
        False, description='Indica se é coordenador do projeto'
    )


class ResearchProjectProduction(BaseModel):
    """Produção declarada como resultado do projeto."""

    title: Optional[str] = Field(None, description='Título da produção')
    type: Optional[str] = Field(None, description='Tipo da produção')


class ResearchProjectSummary(BaseModel):
    """Card resumido de projeto de pesquisa."""

    id: UUID = Field(description='ID canônico do projeto')
    title: str = Field(description='Nome do projeto')
    start_year: Optional[int] = Field(None, description='Ano de início')
    end_year: Optional[int] = Field(
        None, description='Ano de término (ausente se em andamento)'
    )
    status: Optional[str] = Field(
        None, description='Situação (ex.: EM_ANDAMENTO, CONCLUIDO)'
    )
    nature: Optional[str] = Field(
        None, description='Natureza (ex.: PESQUISA, EXTENSAO)'
    )
    agency_name: Optional[str] = Field(
        None, description='Agência financiadora principal'
    )
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Integrantes da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class ResearchProjectDetail(ResearchProjectSummary):
    """Dossiê detalhado de projeto de pesquisa."""

    agency_code: Optional[str] = Field(
        None, description='Código da agência financiadora principal'
    )
    description: Optional[str] = Field(
        None, description='Descrição do projeto'
    )
    number_undergraduates: Optional[int] = Field(
        None, description='Número de alunos de graduação'
    )
    number_specialists: Optional[int] = Field(
        None, description='Número de alunos de especialização'
    )
    number_academic_masters: Optional[int] = Field(
        None, description='Número de alunos de mestrado acadêmico'
    )
    number_phd: Optional[int] = Field(
        None, description='Número de alunos de doutorado'
    )
    foment: list[ResearchProjectFoment] = Field(
        default_factory=list, description='Financiamentos do projeto'
    )
    components: list[ResearchProjectComponent] = Field(
        default_factory=list, description='Integrantes declarados no Lattes'
    )
    productions: list[ResearchProjectProduction] = Field(
        default_factory=list, description='Produções vinculadas ao projeto'
    )


class ResearchProjectFilter(ProductionBaseFilter):
    """Filtros para busca de projetos de pesquisa.

    `year_start`/`year_end` se aplicam ao ano de início do projeto.
    """

    status: list[str] = Field(
        default_factory=list,
        description='Situação do projeto (ex.: EM_ANDAMENTO, CONCLUIDO)',
    )
    nature: list[str] = Field(
        default_factory=list,
        description='Natureza do projeto (ex.: PESQUISA, EXTENSAO)',
    )


class ResearchProjectSearchResponse(BaseModel):
    """Resposta paginada da busca de projetos de pesquisa."""

    data: list[ResearchProjectSummary]
    pagination: Pagination
    filters_applied: ResearchProjectFilter
    sort: ProductionSort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None
