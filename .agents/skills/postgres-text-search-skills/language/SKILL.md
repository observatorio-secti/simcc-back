---
name: postgres-text-search-language
description: Configura idiomas, stemming, stop words, dicionários, sinônimos e acentuação no PostgreSQL FTS.
---

# PostgreSQL Language Search

Cada documento e consulta deve usar uma configuração linguística coerente.

Exemplo:

```sql
to_tsvector('portuguese', content)
websearch_to_tsquery('portuguese', $1)
```

Para documentos em múltiplos idiomas, armazene a configuração por documento ou use uma estratégia de particionamento/desnormalização que mantenha documento e consulta na mesma configuração.

O PostgreSQL fornece configurações e dicionários para diversos idiomas e permite criar configurações próprias.

Para acentos, use `unaccent` quando a regra de negócio for busca insensível a diacríticos:

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;
```

Para uma configuração customizada, `unaccent` pode ser colocado antes do stemmer no mapeamento de dicionários.

Não trate remoção de acentos como sempre correta. Nomes próprios, identificadores e termos técnicos podem exigir comportamento diferente.

Para depuração:

```sql
SELECT *
FROM ts_debug('portuguese', 'ação brasileira');
```

Quando a configuração de busca mudar, reavalie os vetores persistidos e os índices derivados dela.
