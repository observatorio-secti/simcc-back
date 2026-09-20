---
name: postgres-text-search-indexing
description: Escolhe e mantém índices para Full Text Search e pg_trgm no PostgreSQL.
---

# PostgreSQL Search Indexing

Para `tsvector`, GIN é normalmente a escolha padrão:

```sql
CREATE INDEX post_search_gin
ON post USING gin (search_vector);
```

GiST também suporta text search, mas tem comportamento diferente e pode ser útil em cenários específicos.

Para trigramas:

```sql
CREATE INDEX product_name_trgm
ON product USING gin (name gin_trgm_ops);
```

Ou use GiST quando a ordenação por distância e as características do workload justificarem.

Expressões indexadas devem respeitar as regras de imutabilidade. Para FTS indexável, declare a configuração de forma explícita em vez de depender de `default_text_search_config`.

Para dados da própria linha, considere `tsvector` armazenado ou generated column. Para dados vindos de joins, generated columns e índices de expressão não podem substituir uma etapa de materialização que depende de outras linhas ou tabelas.

Após criar índices, valide com:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...
```

Não presuma que um índice será usado apenas porque existe. Cardinalidade, seletividade, custo e forma da consulta determinam o plano.
