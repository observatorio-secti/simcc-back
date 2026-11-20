"""Vocabulário único de tipos da v2, em snake_case minúsculo.

O mesmo valor vale em rota, filtro, faceta, evidência e sugestão. O banco
continua com os valores antigos (`BOOK_CHAPTER`, `PARTICIPATION_EVENT`...):
a tradução fica aqui, em `to_db`/`from_db`. Na entrada, os valores antigos
são aceitos como alias.
"""

from typing import Annotated, Any, Literal

from pydantic import BeforeValidator

# Tipos de produção servidos em /v2/production/{kind} (no caminho, com
# hífen: book-chapter, research-project)
ProductionKind = Literal[
    'article',
    'book',
    'book_chapter',
    'software',
    'patent',
    'event',
    'research_project',
    'brand',
    'guidance',
    'report',
]

# Origens de evidência na busca de pesquisadores (`mv_search_documents`)
SourceType = Literal[
    'article',
    'book',
    'book_chapter',
    'patent',
    'software',
    'event',
    'area_specialty',
]

# Origem de uma evidência: as obras acima ou o próprio perfil
MatchSourceType = Literal[
    'article',
    'book',
    'book_chapter',
    'patent',
    'software',
    'event',
    'area_specialty',
    'profile',
]

# Dicionários de termos (`research_dictionary.type_`)
DictionaryType = Literal[
    'article',
    'book',
    'book_chapter',
    'patent',
    'speaker',
    'abstract',
]

_DB_OVERRIDES = {'event': 'PARTICIPATION_EVENT'}
_FROM_DB_OVERRIDES = {v: k for k, v in _DB_OVERRIDES.items()}
_INPUT_ALIASES = {
    'participation_event': 'event',
    'area': 'area_specialty',
    'book-chapter': 'book_chapter',
    'research-project': 'research_project',
}


def to_db(value: str) -> str:
    """Valor da API → valor gravado no banco."""
    return _DB_OVERRIDES.get(value, value.upper())


def from_db(value: str) -> str:
    """Valor do banco → valor da API."""
    return _FROM_DB_OVERRIDES.get(value, value.lower())


def normalize_kind(value: Any) -> Any:
    """Aceita o formato novo e os antigos (`BOOK_CHAPTER`, `EVENT`...)."""
    if not isinstance(value, str):
        return value
    lowered = value.strip().lower()
    return _INPUT_ALIASES.get(lowered, lowered)


def normalize_kind_list(value: Any) -> Any:
    if isinstance(value, str):
        value = [value]
    if isinstance(value, (list, tuple, set)):
        return [normalize_kind(item) for item in value if item]
    return value


# Tipos de entrada: mesmo enum no OpenAPI, aceitando os valores antigos.
# A normalização fica no tipo (e não num validador do model) porque o
# FastAPI valida cada parâmetro de query antes de montar o model.
SourceTypeParam = Annotated[SourceType, BeforeValidator(normalize_kind)]
DictionaryTypeParam = Annotated[
    DictionaryType, BeforeValidator(normalize_kind)
]
