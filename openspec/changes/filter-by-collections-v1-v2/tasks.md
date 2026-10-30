# Tasks

## 1. Models e Migrations
- [x] 1.1 Criar model `Collection` e `ResearcherCollection` em `simcc/core/db/models/collection.py`.
- [x] 1.2 Criar migration Alembic para criar `collection`, `researcher_collection` e recriar `mv_researcher_search` com `collection_slugs` e índice GIN.
- [x] 1.3 Atualizar `search_tables.py` com `collection_slugs`.

## 2. API v2
- [x] 2.1 Adicionar `collection` em `ResearcherFilter` e registrar `_by_collections` em `researcher_filters.py`.
- [x] 2.2 Adicionar `collection` em `ProductionBaseFilter` e aplicar filtro em `production_repo.py` e `article_repo.py`.

## 3. API v1
- [x] 3.1 Adicionar `collection` em `DefaultFilters`.
- [x] 3.2 Atualizar `ResearcherSearchQuery`, `ResearcherFilterQuery`, `OutstandingResearchersQuery`, `production_query.py` e `metrics_query.py` com o filtro de coleção e remoção de `r.status` e `r.institution_id`.
