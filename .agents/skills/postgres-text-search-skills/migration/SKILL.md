---
name: postgres-text-search-migration
description: Valida compatibilidade de busca textual durante upgrades do PostgreSQL.
---

# PostgreSQL Search Migration

O material original é de 2015 e usa PostgreSQL 9.5 como referência. O núcleo de FTS continua válido, mas o baseline atual é PostgreSQL 18.x.

No PostgreSQL 18, a busca textual passou a usar o provider de collation padrão do cluster para ler arquivos de configuração e dicionários, em vez de sempre usar libc. Upgrades com mudança relevante de collation podem exigir reindexação de índices de Full Text Search e `pg_trgm`.

PostgreSQL 18 também adicionou stemming para estoniano e atualizou dados Unicode para Unicode 16.0.

Após upgrade:

```sql
SHOW server_version;
SHOW lc_collate;
SHOW default_text_search_config;
```

Teste:

```sql
SELECT to_tsvector('portuguese', 'ações e ação');
SELECT websearch_to_tsquery('portuguese', '"ação"');
```

Audite índices relacionados a `tsvector` e `pg_trgm`.

Se o upgrade alterar a semântica de collation ou dicionários, planeje reindexação. Não considere uma migração de versão concluída apenas porque o banco iniciou corretamente.
