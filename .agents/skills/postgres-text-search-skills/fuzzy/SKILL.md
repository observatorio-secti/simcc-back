---
name: postgres-text-search-fuzzy
description: Implementa tolerância a erros, similaridade textual, sugestões e buscas aproximadas com pg_trgm.
---

# PostgreSQL Fuzzy Search

Ative:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

Para similaridade entre strings:

```sql
SELECT similarity($1, $2);
```

Para busca indexável por similaridade:

```sql
SELECT name
FROM product
WHERE name % $1
ORDER BY name <-> $1
LIMIT 10;
```

Crie o índice conforme o padrão de acesso:

```sql
CREATE INDEX product_name_trgm_gin
ON product USING gin (name gin_trgm_ops);
```

`pg_trgm` também pode acelerar determinados `LIKE`, `ILIKE`, regex e igualdade por meio dos operator classes de trigramas.

Use `word_similarity` ou `strict_word_similarity` quando a unidade de comparação for uma extensão de palavras dentro de um texto maior.

Não copie o limiar `0.5` do material antigo como regra geral. Os limiares atuais são configuráveis e dependem da distribuição dos dados e do objetivo da busca.

Para correção ortográfica, prefira gerar sugestões com candidatos indexados e validar a qualidade empiricamente.
