# Proposal: Suporte a Coleções no Banco Público, MVs e Filtros de Pesquisadores e Produções (v1 e v2)

## Why

1. O banco público do SimCC agora recebe pesquisadores de múltiplos projetos/coleções (`simcc`, `fomento`, etc.).
2. Por padrão, a API pública e o portal devem retornar apenas os pesquisadores da coleção principal (`simcc`).
3. Deve ser possível buscar pesquisadores de outras coleções ou de todas as coleções informando `?collection=<slug>` ou `?collection=all` (ou `*`).
4. As rotas de produções científicas (`/v2/production/*`) e métricas também devem filtrar por coleção por padrão para evitar inflar contadores e listagens com obras de pesquisadores exclusivos de outros projetos.
5. Os campos `researcher.institution_id`, `status` e `extra_field` foram descontinuados; todas as buscas v1 e v2 devem usar unicamente `researcher_institution` e `researcher_collection`.

## What Changes

- Modelagem e Migrations:
  - Criação das tabelas `collection` e `researcher_collection`.
  - Atualização da `mv_researcher_search` para agregar `collection_slugs TEXT[]` com índice GIN.
- API v2:
  - Adição do filtro `collection` (padrão `['simcc']`) em `ResearcherFilter` e `ProductionBaseFilter`.
  - Tratamento de `all` / `*` para liberar o filtro e buscar em todas as coleções.
- API v1:
  - Adição do filtro `collection` (padrão `'simcc'`) em `DefaultFilters`.
  - Remoção de `r.status IS True` e de joins legados com `r.institution_id` em todas as queries (`ResearcherSearchQuery`, `ResearcherFilterQuery`, `OutstandingResearchersQuery`, `production_query.py`, `metrics_query.py`).
