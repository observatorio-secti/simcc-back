---
name: postgres-text-search-troubleshooting
description: Diagnostica resultados incorretos, ausência de resultados, stemming, idioma, índices e problemas de manutenção em FTS.
---

# PostgreSQL Search Troubleshooting

Quando não há resultados:

1. execute `to_tsvector` com a configuração usada pelo documento;
2. execute a função de query com a mesma configuração;
3. use `ts_debug`;
4. verifique stop words;
5. verifique stemming;
6. verifique acentos;
7. verifique se o campo foi incluído no vetor;
8. verifique se o índice está atualizado.

Quando o resultado está excessivo:

1. revise stop words;
2. revise stemming;
3. use pesos;
4. restrinja campos;
5. ajuste a consulta;
6. combine FTS com filtros estruturados.

Quando o índice não é usado:

1. rode `EXPLAIN (ANALYZE, BUFFERS)`;
2. confira a forma exata do predicado;
3. confira seletividade;
4. confira estatísticas;
5. confira se a expressão indexada é a mesma expressão usada na consulta;
6. verifique tamanho e custo do índice.

Quando a busca muda depois de upgrade:

1. confira `server_version`;
2. confira configurações e dicionários;
3. confira collations;
4. reavalie índices FTS e `pg_trgm`;
5. execute testes de regressão da busca.

Não corrija um índice inconsistente alterando funções para `IMMUTABLE` sem compreender a consequência. Configurações e dicionários de text search fazem parte da semântica do índice.
