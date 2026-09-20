---
name: postgres-text-search-architecture
description: Modela documentos de busca derivados de múltiplas tabelas e escolhe entre coluna derivada, trigger, materialização e processamento assíncrono.
---

# PostgreSQL Search Architecture

Primeiro defina o documento lógico. Ele pode combinar título, conteúdo, autor, tags e outros atributos.

Se todos os campos pertencem à mesma linha, prefira manter o vetor junto da linha.

Se o documento depende de várias tabelas, avalie:

1. desnormalização controlada;
2. trigger para atualização síncrona;
3. tabela de índice de busca atualizada pela aplicação;
4. materialized view para cenários com atraso aceitável;
5. processamento assíncrono para workloads maiores.

Materialized view é adequada quando atraso de atualização é aceitável e o custo de reconstrução é controlável. Não trate `REFRESH MATERIALIZED VIEW` como solução universal para alta frequência de escrita.

Ao usar joins para construir o documento, preserve linhas sem tags com `LEFT JOIN` quando elas também devem ser pesquisáveis.

Exemplo:

```sql
SELECT
    post.id,
    setweight(to_tsvector('portuguese', coalesce(post.title, '')), 'A') ||
    setweight(to_tsvector('portuguese', coalesce(post.content, '')), 'B') ||
    setweight(to_tsvector('simple', coalesce(author.name, '')), 'C') ||
    setweight(to_tsvector('simple', coalesce(string_agg(tag.name, ' '), '')), 'B') AS search_vector
FROM post
JOIN author ON author.id = post.author_id
LEFT JOIN posts_tags ON posts_tags.post_id = post.id
LEFT JOIN tag ON tag.id = posts_tags.tag_id
GROUP BY post.id, author.id;
```

Evite construir o documento repetidamente na consulta de leitura se a busca for frequente. Materialize o `tsvector` quando isso reduzir custo de CPU e permitir um índice eficiente.
