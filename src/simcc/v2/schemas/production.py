"""Schemas V2 para produções científicas (Artigos, Livros, etc.)."""

from datetime import datetime
from typing import Any, ClassVar, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from simcc.v2.schemas.base import V2Model
from simcc.v2.schemas.params import Pagination
from simcc.v2.schemas.qualis import (
    QualisFilterValue,
    QualisRank,
    QualisStatus,
    parse_jcr,
    parse_qualis,
)
from simcc.v2.schemas.researcher import FacetResult, Meta, Sort

MIN_VALID_YEAR = 1900
MAX_VALID_YEAR = 2100


class ResearcherRef(V2Model):
    """Referência enxuta a um pesquisador cadastrado na plataforma."""

    id: UUID = Field(description='Identificador do pesquisador')
    name: str = Field(description='Nome do pesquisador')
    lattes_id: Optional[str] = Field(None, description='ID Lattes')


class MagazineRef(V2Model):
    """Informações do periódico/revista onde o artigo foi publicado."""

    name: Optional[str] = Field(None, description='Nome da revista/periódico')
    issn: Optional[str] = Field(None, description='ISSN da publicação')
    qualis: Optional[QualisRank] = Field(
        None, description='Estrato Qualis CAPES; null quando não houver'
    )
    qualis_status: Optional[QualisStatus] = Field(
        None,
        description=(
            'Motivo da ausência de estrato: not_rated (sem Qualis) ou '
            'not_applicable (não se aplica)'
        ),
    )
    jcr: Optional[float] = Field(None, description='Fator de impacto JCR')

    @model_validator(mode='before')
    @classmethod
    def _type_qualis_and_jcr(cls, data: Any) -> Any:
        """Converte os valores textuais do banco."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        qualis = data.get('qualis')
        if isinstance(qualis, str) and qualis not in QualisRank.__args__:
            rank, status = parse_qualis(qualis)
            data['qualis'] = rank
            data.setdefault('qualis_status', status)
        if 'jcr' in data and not isinstance(data['jcr'], (float, type(None))):
            data['jcr'] = parse_jcr(data['jcr'])
        return data


def split_list(value: Any) -> Any:
    """Texto separado por `;` (ou `,`, se não houver `;`) → lista."""
    if value is None:
        return []
    if not isinstance(value, str):
        return value
    sep = ';' if ';' in value else ','
    return [part.strip() for part in value.split(sep) if part.strip()]


class AuthorName(V2Model):
    """Autor como declarado na publicação."""

    name: str = Field(description='Nome do autor')


def split_authors(raw: Optional[str]) -> list[AuthorName]:
    """Lista de autores a partir do texto do Lattes (separado por `;`).

    É uma separação simples: nomes não são casados com pesquisadores da
    plataforma (esses estão em `platform_authors`).
    """
    if not raw:
        return []
    return [
        AuthorName(name=part.strip())
        for part in raw.split(';')
        if part.strip()
    ]


class _AuthorsMixin(V2Model):
    authors: list[AuthorName] = Field(
        default_factory=list,
        description='Autores separados a partir de `all_authors_raw`',
    )

    @model_validator(mode='after')
    def _fill_authors(self):
        raw = getattr(self, 'all_authors_raw', None)
        if not self.authors and raw:
            self.authors = split_authors(raw)
        return self


class ArticleRef(V2Model):
    """Referência básica a um artigo científico."""

    id: UUID = Field(description='Identificador único canônico do artigo')
    title: str = Field(description='Título do artigo')
    year: Optional[int] = Field(None, description='Ano de publicação')
    doi: Optional[str] = Field(None, description='DOI do artigo')


class ArticleMatch(V2Model):
    """Trecho onde o termo de busca casou na produção."""

    field: str = Field(
        description='Campo onde casou (title, abstract, ...)'
    )
    snippet: str = Field(description='Trecho em texto puro, sem marcação')
    highlights: list[tuple[int, int]] = Field(
        default_factory=list,
        description=(
            'Intervalos [início, fim) destacados em `snippet`, em unidades '
            'UTF-16 (as de String.slice no JavaScript)'
        ),
    )

    @classmethod
    def from_marked(cls, field: str, marked: str) -> 'ArticleMatch':
        """Monta a partir da saída do `ts_headline` com marcadores."""
        from simcc.v2.repositories.highlight import (  # noqa: PLC0415
            parse_highlight,
        )

        snippet, highlights = parse_highlight(marked)
        return cls(field=field, snippet=snippet, highlights=highlights)


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


class ArticleDetail(_AuthorsMixin, ArticleSummary):
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
    keywords: list[str] = Field(
        default_factory=list,
        description='Palavras-chave registradas no OpenAlex',
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
    city_code: list[str] = Field(
        default_factory=list,
        description=(
            'Códigos IBGE dos municípios de vínculo dos autores da plataforma'
        ),
    )
    identity_territory: list[str] = Field(
        default_factory=list,
        description=(
            'Territórios de identidade dos vínculos dos autores da '
            'plataforma: código SEI (1 a 27) ou nome'
        ),
    )
    area: list[str] = Field(
        default_factory=list,
        description='Grande Área do Conhecimento dos autores da plataforma',
    )
    collection: list[str] = Field(
        default_factory=list,
        description="Slugs das coleções (sem filtro por padrão). Use 'all' ou '*' para buscar em todas as coleções",
    )

    @field_validator('collection', mode='before')
    @classmethod
    def _normalize_collection(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [item.strip() for item in v.replace(';', ',').split(',') if item.strip()]
        if isinstance(v, (list, tuple, set)):
            result = []
            for item in v:
                if isinstance(item, str):
                    result.extend([s.strip() for s in item.replace(';', ',').split(',') if s.strip()])
                elif item:
                    result.append(str(item).strip())
            return result
        return v

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

    qualis: list[QualisFilterValue] = Field(
        default_factory=list,
        description=(
            'Estrato Qualis (A1...C) ou ausência (not_rated, '
            'not_applicable). Aceita também SQ e NP'
        ),
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

    sort_by: Literal['relevance', 'year', 'citations', 'title'] = Field(
        'relevance', description='Campo para ordenação'
    )
    sort_order: Literal['asc', 'desc'] = Field(
        'desc', description='Direção da ordenação (asc/desc)'
    )


class ProductionSort(BaseModel):
    """Critério e direção de ordenação padrão para produções."""

    sort_by: Literal['relevance', 'year', 'title'] = Field(
        'relevance', description='Campo para ordenação'
    )
    sort_order: Literal['asc', 'desc'] = Field(
        'desc', description='Direção da ordenação (asc/desc)'
    )


COMMON_PRODUCTION_FACETS = (
    'institution',
    'graduate_program',
    'city',
    'identity_territory',
    'territory_city',
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
    sort: Sort = Field(description='Critério e direção de ordenação')
    meta: Meta = Field(description='Metadados de performance e cache')
    facets: Optional[dict[str, FacetResult]] = Field(
        None, description='Facets solicitados em `facets`'
    )


# =========================================================================
# 1. LIVROS
# =========================================================================

class BookSummary(V2Model):
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


class BookDetail(_AuthorsMixin, BookSummary):
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
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 2. CAPÍTULOS DE LIVROS
# =========================================================================

class BookChapterSummary(V2Model):
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


class BookChapterDetail(_AuthorsMixin, BookChapterSummary):
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
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 3. SOFTWARES
# =========================================================================

class SoftwareSummary(V2Model):
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
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 4. PATENTES
# =========================================================================

class PatentSummary(V2Model):
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
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 5. PARTICIPAÇÃO EM EVENTOS
# =========================================================================

class EventSummary(V2Model):
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
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 6. PROJETOS DE PESQUISA
# =========================================================================

class ResearchProjectFoment(V2Model):
    """Agência financiadora de um projeto de pesquisa."""

    agency_name: Optional[str] = Field(None, description='Nome da agência')
    agency_code: Optional[str] = Field(None, description='Código da agência')
    nature: Optional[str] = Field(
        None, description='Natureza do financiamento (ex.: Bolsa, Auxílio)'
    )


class ResearchProjectComponent(V2Model):
    """Integrante de um projeto de pesquisa, conforme declarado no Lattes."""

    name: Optional[str] = Field(None, description='Nome do integrante')
    lattes_id: Optional[str] = Field(None, description='ID Lattes')
    citations: Optional[str] = Field(
        None, description='Nome em citações bibliográficas'
    )
    coordinator: bool = Field(
        False, description='Indica se é coordenador do projeto'
    )


class ResearchProjectProduction(V2Model):
    """Produção declarada como resultado do projeto."""

    title: Optional[str] = Field(None, description='Título da produção')
    type: Optional[str] = Field(None, description='Tipo da produção')


class ResearchProjectSummary(V2Model):
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
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 7. MARCAS
# =========================================================================


class BrandSummary(V2Model):
    """Card resumido de marca registrada."""

    id: UUID = Field(description='ID canônico da marca')
    title: str = Field(description='Nome da marca')
    year: Optional[int] = Field(None, description='Ano')
    nature: Optional[str] = Field(None, description='Natureza da marca')
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Titulares da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class BrandDetail(BrandSummary):
    """Dossiê detalhado de marca."""

    goal: Optional[str] = Field(None, description='Finalidade da marca')


class BrandFilter(ProductionBaseFilter):
    """Filtros para busca de marcas."""

    nature: list[str] = Field(
        default_factory=list, description='Natureza da marca'
    )


class BrandSearchResponse(BaseModel):
    """Resposta paginada da busca de marcas."""

    data: list[BrandSummary]
    pagination: Pagination
    filters_applied: BrandFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 8. ORIENTAÇÕES
# =========================================================================


class GuidanceSummary(V2Model):
    """Card resumido de orientação."""

    id: UUID = Field(description='ID canônico da orientação')
    title: str = Field(description='Título do trabalho orientado')
    year: Optional[int] = Field(None, description='Ano')
    nature: Optional[str] = Field(
        None, description='Natureza (ex.: Dissertação de mestrado)'
    )
    type: Optional[str] = Field(
        None, description='Tipo (ex.: Orientador principal)'
    )
    status: Optional[str] = Field(
        None, description='Situação (ex.: Concluída, Em andamento)'
    )
    oriented: Optional[str] = Field(None, description='Nome do orientando')
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Orientadores da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class GuidanceDetail(GuidanceSummary):
    """Dossiê detalhado de orientação."""


class GuidanceFilter(ProductionBaseFilter):
    """Filtros para busca de orientações."""

    nature: list[str] = Field(
        default_factory=list, description='Natureza da orientação'
    )
    type: list[str] = Field(
        default_factory=list, description='Tipo de orientação'
    )
    status: list[str] = Field(
        default_factory=list, description='Situação da orientação'
    )


class GuidanceSearchResponse(BaseModel):
    """Resposta paginada da busca de orientações."""

    data: list[GuidanceSummary]
    pagination: Pagination
    filters_applied: GuidanceFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 9. RELATÓRIOS TÉCNICOS
# =========================================================================


class ReportSummary(V2Model):
    """Card resumido de relatório técnico."""

    id: UUID = Field(description='ID canônico do relatório')
    title: str = Field(description='Título do relatório')
    year: Optional[int] = Field(None, description='Ano')
    project_name: Optional[str] = Field(
        None, description='Projeto relacionado'
    )
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Autores da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class ReportDetail(ReportSummary):
    """Dossiê detalhado de relatório técnico."""

    financing: Optional[str] = Field(
        None, description='Instituição financiadora'
    )


class ReportFilter(ProductionBaseFilter):
    """Filtros para busca de relatórios técnicos."""


class ReportSearchResponse(BaseModel):
    """Resposta paginada da busca de relatórios técnicos."""

    data: list[ReportSummary]
    pagination: Pagination
    filters_applied: ReportFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 10. TEXTOS EM REVISTA / JORNAL
# =========================================================================


class MagazineTextSummary(V2Model):
    """Card resumido de texto em jornal ou revista."""

    id: UUID = Field(description='ID canônico do texto')
    title: str = Field(description='Título do texto')
    year: Optional[int] = Field(None, description='Ano de publicação')
    nature: Optional[str] = Field(None, description='Natureza do texto')
    language: Optional[str] = Field(None, description='Idioma')
    means_divulgation: Optional[str] = Field(
        None, description='Meio de divulgação'
    )
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Autores da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class MagazineTextDetail(MagazineTextSummary):
    """Dossiê detalhado de texto em jornal ou revista."""

    title_en: Optional[str] = Field(None, description='Título em inglês')
    homepage: Optional[str] = Field(None, description='URL do texto')
    relevance: Optional[bool] = Field(None, description='Produção relevante')
    scientific_divulgation: Optional[bool] = Field(
        None, description='Divulgação científica'
    )
    all_authors_raw: Optional[str] = Field(
        None, description='Lista bruta de autores'
    )


class MagazineTextFilter(ProductionBaseFilter):
    """Filtros para busca de textos em jornal ou revista."""

    nature: list[str] = Field(
        default_factory=list, description='Natureza do texto'
    )


class MagazineTextSearchResponse(BaseModel):
    """Resposta paginada da busca de textos em jornal ou revista."""

    data: list[MagazineTextSummary]
    pagination: Pagination
    filters_applied: MagazineTextFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None


# =========================================================================
# 11. TRABALHOS EM EVENTOS
# =========================================================================


class EventWorkSummary(V2Model):
    """Card resumido de trabalho publicado em evento."""

    id: UUID = Field(description='ID canônico do trabalho em evento')
    title: str = Field(description='Título do trabalho')
    year: Optional[int] = Field(None, description='Ano de publicação')
    nature: Optional[str] = Field(None, description='Natureza do trabalho')
    event_name: Optional[str] = Field(None, description='Nome do evento')
    event_classification: Optional[str] = Field(
        None, description='Classificação do evento'
    )
    platform_authors: list[ResearcherRef] = Field(
        default_factory=list, description='Autores da plataforma'
    )
    matches: Optional[list[ArticleMatch]] = Field(None, description='Matches')


class EventWorkDetail(EventWorkSummary):
    """Dossiê detalhado de trabalho publicado em evento."""

    title_en: Optional[str] = Field(None, description='Título em inglês')
    language: Optional[str] = Field(None, description='Idioma')
    means_divulgation: Optional[str] = Field(
        None, description='Meio de divulgação'
    )
    homepage: Optional[str] = Field(None, description='URL do trabalho')
    relevance: Optional[bool] = Field(None, description='Produção relevante')
    scientific_divulgation: Optional[bool] = Field(
        None, description='Divulgação científica'
    )
    all_authors_raw: Optional[str] = Field(
        None, description='Lista bruta de autores'
    )
    event_city: Optional[str] = Field(None, description='Cidade do evento')
    event_year: Optional[int] = Field(None, description='Ano do evento')
    proceedings_title: Optional[str] = Field(
        None, description='Título dos anais'
    )
    volume: Optional[str] = Field(None, description='Volume')
    issue: Optional[str] = Field(None, description='Fascículo')
    series: Optional[str] = Field(None, description='Série')
    start_page: Optional[str] = Field(None, description='Página inicial')
    end_page: Optional[str] = Field(None, description='Página final')
    publisher_name: Optional[str] = Field(None, description='Editora')
    publisher_city: Optional[str] = Field(None, description='Cidade da editora')
    isbn: Optional[str] = Field(None, description='ISBN dos anais')


class EventWorkFilter(ProductionBaseFilter):
    """Filtros para busca de trabalhos em eventos."""

    nature: list[str] = Field(
        default_factory=list, description='Natureza do trabalho'
    )
    event_classification: list[str] = Field(
        default_factory=list, description='Classificação do evento'
    )


class EventWorkSearchResponse(BaseModel):
    """Resposta paginada da busca de trabalhos em eventos."""

    data: list[EventWorkSummary]
    pagination: Pagination
    filters_applied: EventWorkFilter
    sort: Sort
    meta: Meta
    facets: Optional[dict[str, FacetResult]] = None
