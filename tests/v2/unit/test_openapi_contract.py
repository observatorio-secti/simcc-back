"""O contrato publicado (`/v2/openapi.json`) é versionado em
`docs/openapi-v2.json`. Mudanças no contrato aparecem no diff do PR.

Para atualizar o arquivo depois de uma mudança intencional:

    UPDATE_OPENAPI=1 poetry run pytest tests/v2/unit/test_openapi_contract.py
"""

import json
import os
from pathlib import Path

from simcc.v2 import v2_app

SNAPSHOT = Path(__file__).parents[3] / 'docs' / 'openapi-v2.json'


def _current() -> str:
    v2_app.openapi_schema = None
    schema = v2_app.openapi()
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True)


def test_openapi_matches_versioned_snapshot():
    current = _current() + '\n'
    if os.environ.get('UPDATE_OPENAPI') == '1':
        SNAPSHOT.write_text(current, encoding='utf-8')
    assert SNAPSHOT.exists(), (
        'docs/openapi-v2.json não existe; gere com UPDATE_OPENAPI=1'
    )
    assert SNAPSHOT.read_text(encoding='utf-8') == current, (
        'O contrato v2 mudou. Se a mudança é intencional, regenere com '
        'UPDATE_OPENAPI=1 e registre em docs/changelog-v2.md'
    )


def test_openapi_has_no_untyped_fields():
    """Nenhum campo de resposta sem tipo (`unknown` no gerador do front)."""
    schemas = json.loads(_current())['components']['schemas']
    untyped = [
        f'{name}.{prop}'
        for name, schema in schemas.items()
        for prop, spec in schema.get('properties', {}).items()
        if spec in ({}, {'title': spec.get('title')})
    ]
    assert untyped == []


def test_openapi_schemas_publish_their_fields():
    """Nenhum modelo de resposta publicado como objeto sem propriedades.

    Um `model_serializer(mode='wrap')` faz o pydantic publicar o schema de
    saída como dicionário qualquer, e o gerador do front perde os campos.
    Para omitir campos nulos, use `Field(exclude_if=...)`."""
    schemas = json.loads(_current())['components']['schemas']
    opaque = [
        name
        for name, schema in schemas.items()
        if schema.get('type') == 'object' and 'properties' not in schema
    ]
    assert opaque == []


def test_openapi_facet_schemas_have_all_fields():
    schemas = json.loads(_current())['components']['schemas']
    assert set(schemas['FacetItem']['properties']) == {
        'value',
        'label',
        'count',
        'acronym',
        'code',
        'selected',
        'children',
    }
    assert set(schemas['FacetResult']['properties']) == {
        'param',
        'total',
        'covered',
        'items',
    }
