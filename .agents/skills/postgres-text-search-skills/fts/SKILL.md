---
name: postgres-text-search-fts
description: Implementa e diagnostica Full Text Search nativo do PostgreSQL com tsvector, tsquery e @@.
---

# PostgreSQL Full Text Search

Use `to_tsvector` para transformar texto em lexemas normalizados e `to_tsquery`, `plainto_tsquery`, `phraseto_tsquery` ou `websearch_to_tsquery` para construir consultas.

Prefira uma configuração explícita:

```sql
to_tsvector('portuguese', text)
```

Para entrada livre:

```sql
websearch_to_tsquery('portuguese', $1)
```

Para frase controlada:

```sql
phraseto_tsquery('portuguese', $1)
```

Para sintaxe booleana controlada:

```sql
to_tsquery('portuguese', $1)
```

O operador de correspondência é:

```sql
search_vector @@ query
```

Use `coalesce` em campos que podem ser `NULL`.

```sql
setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
setweight(to_tsvector('portuguese', coalesce(content, '')), 'B')
```

Explique que stemming e stop words dependem da configuração e dos dicionários. Não confunda stemming com semântica ou correção ortográfica.

Quando o usuário pergunta por que um termo não aparece, use `ts_debug` e compare o `tsvector` produzido com a consulta normalizada.
