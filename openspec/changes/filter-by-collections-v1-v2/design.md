# Design: Suporte a Coleções no Banco Público, MVs e Filtros de Pesquisadores e Produções (v1 e v2)

## Decisões

1. **Tabelas de Coleção no simcc-back**:
   - `collection`: `id` UUID PK, `slug` VARCHAR UNIQUE, `name` VARCHAR, `description` TEXT, `refresh_interval_days` INT, `is_default` BOOLEAN, `created_at` TIMESTAMP.
   - `researcher_collection`: `id` UUID PK, `researcher_id` UUID FK CASCADE, `collection_id` UUID FK CASCADE, `attributes` JSONB, `created_at` TIMESTAMP.
2. **Atualização da `mv_researcher_search`**:
   - Adicionar CTE `coll_agg` com `array_agg(DISTINCT c.slug) FILTER (WHERE c.slug IS NOT NULL) AS collection_slugs`.
   - Coluna `collection_slugs` com índice GIN.
3. **Filtro na v2**:
   - `ResearcherFilter`: `collection: list[str] = Field(default_factory=lambda: ['simcc'])`.
   - Se `collection` contiver `'all'` ou `'*'`, o filtro não é aplicado.
   - Caso contrário, `mv_researcher_search.c.collection_slugs.overlap(normalized)`.
   - `ProductionBaseFilter`: mesmo filtro, filtrando produções cujos `researcher_ids` têm interseção com os pesquisadores da coleção ativa.
4. **Filtro na v1**:
   - `DefaultFilters`: `collection: Optional[str] = 'simcc'`.
   - Aceita múltiplos slugs separados por vírgula ou ponto-e-vírgula.
   - `collection='all'` ou `'*'` remove o filtro.
   - Remover qualquer menção a `r.status IS True` e `r.institution_id`.
