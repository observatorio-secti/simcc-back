---
name: postgres-text-search
description: Roteia tarefas de busca textual no PostgreSQL para skills especializadas. Use para FTS, ranking, busca por frase, busca web-like, fuzzy search, acentuação, múltiplos idiomas, indexação, manutenção, arquitetura e troubleshooting.
---

# PostgreSQL Text Search Router

## Objetivo

Tratar PostgreSQL como motor de busca textual quando os requisitos puderem ser resolvidos com recursos nativos e extensões fornecidas pelo PostgreSQL. Separar Full Text Search, similaridade por trigramas, normalização, ranking, idioma, indexação e arquitetura em competências específicas.

## Regra de roteamento

Antes de responder, identifique o tipo principal da solicitação:

- `postgres-text-search-fts`: tsvector, tsquery, @@, stemming, stop words, operadores AND/OR/NOT, frases, websearch.
- `postgres-text-search-ranking`: ts_rank, ts_rank_cd, setweight, relevância por campo, ordenação e combinação de sinais.
- `postgres-text-search-fuzzy`: pg_trgm, similarity, word_similarity, strict_word_similarity, %, <->, sugestões e erros de digitação.
- `postgres-text-search-language`: regconfig, português, inglês, múltiplos idiomas, dicionários, configurações customizadas e unaccent.
- `postgres-text-search-indexing`: GIN, GiST, índices de expressão, colunas tsvector, generated columns, triggers e planos de execução.
- `postgres-text-search-architecture`: documento lógico, dados normalizados em várias tabelas, atualização assíncrona, materialized view, consistência e escalabilidade.
- `postgres-text-search-troubleshooting`: resultados ausentes, stemming inesperado, stop words, idioma incorreto, índice não utilizado, configuração alterada e migração.
- `postgres-text-search-migration`: atualização de versão, mudanças de collation, reindexação, compatibilidade e validação pós-upgrade.

Se a tarefa envolver mais de uma área, componha as skills na ordem: arquitetura -> idioma/normalização -> FTS -> ranking/fuzzy -> indexação -> troubleshooting.

## Baseline atual

O alvo deste skill é PostgreSQL 18.x. A API central de Full Text Search continua baseada em `tsvector`, `tsquery`, `@@`, `to_tsvector`, `to_tsquery`, `plainto_tsquery`, `phraseto_tsquery`, `websearch_to_tsquery`, `ts_rank`, `ts_rank_cd`, `setweight` e índices GIN/GiST.

Não assuma `default_text_search_config` em código indexável. Prefira declarar explicitamente a configuração quando a expressão precisar ser indexada.

Use GIN como padrão para busca recorrente em `tsvector`, salvo requisito específico que justifique GiST.

Use `websearch_to_tsquery` para entrada livre de usuário quando a sintaxe desejada for semelhante a buscadores web. Use `to_tsquery` quando a aplicação controla e valida uma sintaxe de consulta estruturada.

Use `pg_trgm` para similaridade textual, autocomplete aproximado, tolerância a erros e consultas por `LIKE`/`ILIKE` que se beneficiem de trigramas. Não trate `pg_trgm` como substituto de stemming ou de relevância semântica.

Use `unaccent` quando a aplicação exigir busca insensível a diacríticos. A decisão deve ser explícita: preservar ou ignorar acentos é uma regra de produto.

Para dados derivados apenas de colunas da mesma linha, avalie uma coluna `tsvector` mantida automaticamente, inclusive generated column quando a expressão e o ciclo de atualização forem compatíveis com as restrições de generated columns. Para documentos que dependem de outras tabelas, não tente colocar joins ou subqueries em generated columns ou índices de expressão; considere desnormalização, trigger ou processo assíncrono.

## Processo de decisão

1. Descobrir a versão real:
   `SHOW server_version;`
   `SHOW server_version_num;`

2. Definir o documento lógico:
   quais campos são pesquisáveis, quais devem pesar mais, quais idiomas existem e quais campos não devem ser indexados.

3. Definir o comportamento da consulta:
   termos livres, operadores booleanos, frases, prefixos, fuzzy, filtros estruturados ou combinação.

4. Escolher a normalização:
   configuração de idioma, stemming, stop words, sinônimos, unaccent e regras específicas.

5. Construir o `tsvector`:
   combinar campos com `||` e usar `setweight` quando a origem do lexema precisar influenciar o ranking.

6. Escolher a estratégia de manutenção:
   expressão direta, coluna derivada, generated column, trigger, tabela desnormalizada ou materialized view.

7. Criar o índice adequado:
   normalmente GIN para `tsvector`; `pg_trgm` com GIN ou GiST para similaridade e padrões suportados.

8. Medir:
   validar com `EXPLAIN (ANALYZE, BUFFERS)`, tamanho do índice, latência, cardinalidade, taxa de atualização e qualidade dos resultados.

9. Validar upgrades:
   testar mudanças de configuração de busca, dicionários, collation e índices. Em upgrades que alterem a interpretação de collation para FTS ou `pg_trgm`, planejar reindexação.

## Padrão de implementação

Quando houver uma tabela simples:

```sql
ALTER TABLE post
ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (
    setweight(to_tsvector('portuguese', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('portuguese', coalesce(content, '')), 'B')
) STORED;

CREATE INDEX post_search_vector_gin
ON post USING gin (search_vector);
```

Quando a consulta vier diretamente do usuário:

```sql
SELECT id, title
FROM post
WHERE search_vector @@ websearch_to_tsquery('portuguese', $1)
ORDER BY ts_rank_cd(search_vector, websearch_to_tsquery('portuguese', $1)) DESC;
```

Não copie esse exemplo sem verificar se o idioma, os pesos, o comportamento de frases e o modelo de atualização correspondem ao domínio.

## Restrições

Não introduza Elasticsearch, OpenSearch ou outro mecanismo externo apenas porque a busca é textual.

Não afirme que PostgreSQL substitui qualquer mecanismo de busca em todos os cenários. Se houver necessidade de recursos como análise linguística muito especializada, busca distribuída em grande escala, agregações de busca complexas ou recursos semânticos/embedding, descreva os limites e avalie uma arquitetura híbrida.

Não use um limiar fixo de `similarity()` como verdade universal. O limiar deve ser calibrado com dados reais.

Não misture `tsvector` e `pg_trgm` sem explicar o papel de cada um.

Não use SQL do material original sem revisar seus joins, aliases, `NULL`, configuração de idioma e indexabilidade.

## Saída esperada

Para uma solicitação técnica, responda nesta ordem:

1. requisito de busca;
2. skill especializada acionada;
3. estratégia PostgreSQL;
4. SQL mínimo funcional;
5. índice e manutenção;
6. limitações e casos de borda;
7. como medir e validar;
8. alternativa externa somente se os requisitos justificarem.
