# SimCC Back · API Pública e Inteligência Científica (`simcc-back`)

API pública de consulta, busca textual e indicadores acadêmicos do **SimCC (Sistema de Mapeamento de Competências Científicas da Bahia)**, integrante do **Ecossistema Observatório CT&I Bahia**.

Este repositório também é o **dono oficial do schema de banco de dados (Alembic)** das 76 tabelas de domínio e das 15 *Materialized Views* utilizadas pelo pipeline [`simcc-etl`](../simcc-etl/README.md) e consultadas pelo agente de IA [`observatorio-maria`](../../observatorio-maria/README.md).

> 📖 **Documentação Conceitual Completa (MkDocs)**: Os conceitos da V2 (Visões Materializadas, Orçamento de Queries, Facets Disjuntivos, Evidências e Guia de Contribuição) estão em [`docs/index.md`](docs/index.md) e podem ser navegados com `poetry run mkdocs serve`. Para o guia de integração ponta a ponta com `simcc-admin` e `simcc-etl`, consulte [`Simcc/README.md`](../README.md).

---

## 🧱 Stack e Arquitetura

- **Python 3.12+**, **FastAPI** (módulos `v1` e `v2`), **Pydantic Settings**
- **SQLAlchemy 2.0 Assíncrono** (`asyncpg` / `psycopg`), **Alembic** e **pgvector**
- **Visões Materializadas em Duas Camadas (`mv_*`)**:
  - `mv_researcher_search`: perfil consolidado para busca textual e facetada de pesquisadores
  - `mv_search_*`: buscas específicas por tipo de produção com índices invertidos GIN (`tsvector`)
  - `mv_canonical_*`: produções desduplicadas (1 linha por obra) para contagens e indicadores globais
- **Redis**: Cache geracional de buscas V2 invalidado atomicamente pelo `simcc-etl` via chave `simcc:v2:search:generation`
- **OpenTelemetry** + **Structlog**: Instrumentação distribuída (FastAPI, SQLAlchemy, Redis, HTTPX) e logs estruturados
- **MkDocs Material**: Portal de documentação técnica e conceitual

---

## 📁 Estrutura de Diretórios

```text
simcc-back/
├── docs/                          # Documentação MkDocs (Conceitos da V2 e Guia de Contribuição)
│   ├── index.md
│   ├── conceitos/                 # Arquitetura, MVs, filtros, facets, cache e logs
│   └── guia-contribuicao/         # Padrões para criação de serviços, endpoints e testes
├── migrations/                    # 36+ migrações Alembic (76 tabelas base + 15 Materialized Views)
├── scripts/                       # Scripts utilitários e manutenção
├── src/simcc/
│   ├── core/                      # Infraestrutura compartilhada
│   │   ├── cache/                 # Cliente Redis e controle de geração de cache
│   │   ├── db/                    # Engine assíncrono (read_db e admin_db) e sessões
│   │   ├── logging/               # Configuração Structlog e OpenTelemetry
│   │   ├── dependencies.py        # Dependências globais FastAPI
│   │   ├── security.py            # Validação de tokens e credenciais
│   │   └── settings.py            # Configurações centralizadas (Pydantic Settings)
│   ├── v1/                        # Endpoints legados, painéis agregados, IA e integrações
│   │   ├── ai/                    # Funcionalidades assistidas por LLM
│   │   ├── queries/               # Consultas analíticas SQL
│   │   ├── repositories/          # Camada de acesso a dados V1
│   │   ├── routers/               # Rotas HTTP V1
│   │   ├── schemas/               # Contratos Pydantic V1
│   │   └── services/              # Regras de negócio V1
│   └── v2/                        # Arquitetura V2 de alta performance (Materialized Views)
│       ├── repositories/          # Consultas otimizadas sobre mv_researcher_search e mv_search_*
│       ├── routers/               # Endpoints de busca V2, sugestões e facetas
│       ├── schemas/               # Filtros defensivos e contratos de resposta V2
│       └── services/              # Orquestração de orçamento de queries, snippets e cache
├── storage/                       # Arquivos locais (seeds CAPES, cache XML, parquet ODA)
├── tests/                         # Suíte de testes unitários e de integração (Testcontainers)
├── alembic.ini                    # Configuração do Alembic
├── compose.yaml                   # Orquestração Docker do serviço e banco de leitura
├── mkdocs.yml                     # Configuração do portal MkDocs Material
└── pyproject.toml                 # Dependências Poetry, Ruff (79 cols, single quotes) e Taskipy
```

---

## 🚀 Como Executar

### 1. Pré-requisitos
- Python 3.12+ e [Poetry](https://python-poetry.org/)
- PostgreSQL (`read_db` na porta `5434` e `admin_db` na porta `5433`) e Redis (`6379`)

### 2. Instalar Dependências
```bash
poetry install
```

### 3. Aplicar Migrações no Banco de Dados
```bash
poetry run alembic upgrade head
```
> **Nota**: No fluxo completo do SimCC, as migrações deste repositório devem ser aplicadas tanto no `read_db` (`5434`) quanto no `write_db` (`5435`) antes de rodar o `simcc-etl`. Veja [`Simcc/README.md`](../README.md#passo-4-executar-as-migrações-alembic-na-ordem-correta).

### 4. Iniciar a API em Modo de Desenvolvimento
```bash
poetry run task run
```
- **API**: `http://localhost:8000`
- **Swagger / OpenAPI**: `http://localhost:8000/swagger` (ou `/docs`)

### 5. Visualizar a Documentação MkDocs
```bash
poetry run mkdocs serve
```

---

## ⚙️ Configuração (`.env`)

Principais variáveis definidas em [`src/simcc/core/settings.py`](src/simcc/core/settings.py):

| Variável | Descrição | Padrão (Dev) |
| :--- | :--- | :--- |
| `DATABASE_URL` | Conexão assíncrona com o banco de leitura (`read_db`) | `postgresql+asyncpg://postgres:postgres@localhost:5434/simcc` |
| `ADMIN_DATABASE_URL` | Conexão assíncrona com o banco administrativo (`simcc-admin`) | `postgresql+asyncpg://db_user:db_password@localhost:5433/db` |
| `REDIS_URL` | URL do Redis para cache das buscas V2 | `redis://localhost:6379/0` |
| `REDIS_ENABLED` | Ativa/desativa o cache Redis | `true` |
| `V2_SEARCH_CACHE_TTL` | Tempo de expiração (segundos) das entradas no Redis | `21600` |
| `URL` | URL pública base da API | `http://localhost:8000` |
| `ADMIN_URL` | URL base do serviço `simcc-admin` | `http://localhost:8009` |
| `ROOT_PATH` | Subcaminho reverso (ex.: `/simcc/api`) para proxy | `""` |
| `OPENAI_API_KEY` | Chave da OpenAI para endpoints de IA (`v1/ai`) | `None` |
| `ODA_API_URL` | URL da Open DGP API (grupos de pesquisa) | `https://oda.vertb.com.br` |
| `OTEL_ENABLED` | Habilita instrumentação OpenTelemetry | `true` (`false` local sem collector) |
| `OTEL_EXPORTER_TYPE` | Tipo de exportador de traces (`otlp`, `console`, `none`) | `none` |

---

## 🧪 Testes, Qualidade e Comandos (`taskipy`)

| Comando | Descrição |
| :--- | :--- |
| `poetry run task run` | Inicia o servidor FastAPI com hot-reload em `src/simcc` |
| `poetry run task test` | Executa a suíte de testes (`pytest -m 'not ai_live'`) com cobertura |
| `poetry run task test_live` | Executa os testes integrados que consomem a API da OpenAI (`-m ai_live`) |
| `poetry run task cov` | Gera o relatório HTML de cobertura em `htmlcov/` |
| `poetry run ruff check .` | Verifica lint e formatação (limite de 79 colunas e aspas simples) |
| `poetry run ruff format .` | Formata o código automaticamente |
