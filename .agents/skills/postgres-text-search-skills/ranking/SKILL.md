---
name: postgres-text-search-ranking
description: Define relevância e ordenação de resultados de Full Text Search no PostgreSQL.
---

# PostgreSQL Ranking

Use `setweight` para representar a origem do lexema:

- `A`: maior peso
- `B`
- `C`
- `D`: menor peso

Exemplo:

```sql
setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
setweight(to_tsvector('portuguese', coalesce(content, '')), 'B')
```

Use `ts_rank` para frequência e pesos e `ts_rank_cd` quando cobertura de posições for relevante.

```sql
ORDER BY ts_rank_cd(search_vector, query) DESC
```

Ranking nativo não conhece a intenção de negócio. Se necessário, combine o score textual com sinais explícitos da aplicação, como recência ou popularidade, sem tratar o score nativo como uma medida universal de relevância.

Valide a qualidade do ranking com conjuntos de consultas reais e métricas da aplicação.
