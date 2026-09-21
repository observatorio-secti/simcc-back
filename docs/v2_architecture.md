# Arquitetura da API V2 e Camadas Funcionais

Esta seção documenta a arquitetura da sub-aplicação **V2**, seus princípios de design orientados a funções (sem classes de serviço ou repositório), a unificação dos schemas de filtros e a especificação do endpoint `/v2/researcher`.

---

## 1. Sub-aplicação V2 (`v2_app`)

A versão 2 do SIMCC Backend é estruturada como uma **sub-aplicação FastAPI modular**, montada na aplicação raiz:

- **Ponto de Entrada**: Localizado em `src/simcc/v2/app.py` e exposto em `src/simcc/v2/__init__.py`.
- **Montagem**: Em `src/simcc/__init__.py`, através do comando `app.mount('/v2', v2_app)`.
- **Documentação Própria**: Possui documentação OpenAPI e Swagger isolada acessível em `/v2/docs` e `/v2/openapi.json`.
- **Isolamento e Testabilidade**: Sincroniza `dependency_overrides` com a aplicação raiz, permitindo testes rápidos de integração e substituição de sessões de banco de dados sem acoplamento.

---

## 2. Princípios de Design: Camadas Enxutas sem Classes

Na versão 1 do SIMCC, a lógica de consulta utilizava classes acumuladoras de estado herdadas de `BaseQuery` (ex: `ResearcherSearchQuery`), gerando complexidade de manutenção, acoplamento e dificuldade de rastreamento.

Na versão 2, adota-se um **design funcional e enxuto**:

```mermaid
flowchart LR
    Request["Cliente / Frontend"] --> Router["Router (FastAPI)"]
    Router -->|Depends(ResearcherFilter)| Service["Service (Função Pura)"]
    Service -->|AsyncSession| Repository["Repository (SQLAlchemy)"]
    Repository -->|Tuple(data, total)| Service
    Service -->|SearchResponse Envelope| Router
    Router --> Response["JSON Response"]
```

- **Sem Classes de Negócio/Repositório**: Todas as camadas operam exclusivamente com funções assíncronas puras.
- **DTOs Claros com Pydantic**: Classes são restritas exclusivamente a modelos de dados e schemas de entrada/saída.
- **Pouca Complexidade**: Fluxo linear unidirecional (`Router -> Service -> Repository -> Banco`).

---

## 3. Schemas de Filtros Unificados (`filters.py`)

Para evitar campos dispersos e duplicações inconsistentes (como `term`, `terms`, `university`, `lenght` da V1), a V2 introduz filtros padronizados centralizados em `src/simcc/v2/schemas/filters.py`:

| Schema | Herança | Campos Padronizados | Aplicação |
|:---|:---|:---|:---|
| `BaseFilter` | `BaseModel` | `q` | Filtro raiz com termo de busca textual unificado. |
| `BaseTemporalFilter` | `BaseFilter` | `q`, `year_start`, `year_end` | Base para entidades que possuem recorte temporal. |
| `ResearcherFilter` | `BaseTemporalFilter` | `q`, `year_start`, `year_end`, `institution_id`, `graduate_program_id` | Filtro de pesquisa de pesquisadores. |
| `ProductionFilter` | `BaseTemporalFilter` | `q`, `year_start`, `year_end`, `institution_id`, `graduate_program_id`, `researcher_id`, `type`, `qualis`, `magazine` | Filtro para produções científicas e tecnológicas. |
| `InstitutionFilter` | `BaseFilter` | `q`, `institution_id`, `state`, `city` | Filtro para listagem e busca de instituições. |
| `GraduateProgramFilter` | `BaseFilter` | `q`, `institution_id`, `area`, `modality`, `rating` | Filtro para programas de pós-graduação. |

> **Injeção de Dependência no FastAPI**: O router consome esses schemas diretamente com `filters: ResearcherFilter = Depends()`, fazendo com que a validação de tipos, valores padrão e documentação automática Swagger ocorram sem código redundante.

---

## 4. Envelope Padrão de Resposta (`SearchResponse`)

Todas as consultas de listagem e busca na V2 compartilham o mesmo envelope estruturado:

- `data`: Lista de entidades retornadas (na fase inicial de pesquisadores, contém `researcher_id` e `name`).
- `pagination`: Metadados de paginação calculados pelo serviço:
  - `page`: Número da página atual.
  - `per_page`: Quantidade de itens por página.
  - `total_items`: Total absoluto de registros encontrados.
  - `total_pages`: Total de páginas disponíveis.
  - `has_next`: Booleano indicando existência de página seguinte.
  - `has_prev`: Booleano indicando existência de página anterior.
- `filters_applied`: Espelho do schema de filtros aplicado na requisição.
- `sort`: Critério de ordenação (`by` e `order`).
- `meta`: Informações de diagnóstico:
  - `took_ms`: Tempo de execução da consulta em milissegundos.
  - `cached`: Indica se o resultado proveio de cache.
  - `timestamp`: Carimbo de data/hora em UTC.
- `facets`: Dicionário opcional para agregação de contadores por facetas (evoluções futuras).
- `summary`: Dicionário opcional para métricas consolidadas (evoluções futuras).

---

## 5. Especificação do Endpoint `GET /v2/researcher`

### Parâmetros de Consulta (Query String)

| Parâmetro | Tipo | Padrão | Validação | Descrição |
|:---|:---|:---|:---|:---|
| `q` | `string` | `null` | Opcional | Termo para busca textual no nome do pesquisador. |
| `year_start` | `integer` | `null` | Opcional | Ano inicial de produções associadas. |
| `year_end` | `integer` | `null` | Opcional | Ano final de produções associadas. |
| `institution_id` | `UUID` | `null` | Opcional | Identificador único da instituição. |
| `graduate_program_id` | `UUID` | `null` | Opcional | Identificador do programa de pós-graduação. |
| `page` | `integer` | `1` | `>= 1` | Número da página desejada. |
| `per_page` | `integer` | `20` | `1 <= n <= 100` | Limite de itens por página. |
| `sort_by` | `string` | `name` | Opcional | Campo para ordenação dos resultados. |
| `sort_order` | `string` | `asc` | `asc` ou `desc` | Direção da ordenação. |

### Exemplo de Resposta (HTTP 200 OK)

```json
{
  "data": [
    {
      "researcher_id": "c71a39f0-2f64-4e20-951b-1d7b32408ec2",
      "name": "Alice V2 Pesquisadora"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  },
  "filters_applied": {
    "q": "Alice",
    "year_start": null,
    "year_end": null,
    "institution_id": null,
    "graduate_program_id": null
  },
  "sort": {
    "by": "name",
    "order": "asc"
  },
  "meta": {
    "took_ms": 3,
    "cached": false,
    "timestamp": "2026-09-21T18:22:56.000Z"
  },
  "facets": null,
  "summary": null
}
```
