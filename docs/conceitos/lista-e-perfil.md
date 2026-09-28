# Lista vs. Perfil do Pesquisador

A V2 separa o pesquisador em duas visões, cada uma com um custo e um propósito:

| | `GET /v2/researcher` | `GET /v2/researcher/{id}` |
|---|---|---|
| **Uso no frontend** | Cards da busca | Página de perfil |
| **Origem dos dados** | `mv_researcher_search` (visão materializada) | Tabelas base (dados sempre atuais) |
| **Consultas ao banco** | 3 + facets + evidências | **4** (perfil, vínculos, programas, grupos) |

Os dois compartilham o mesmo núcleo (`ResearcherBase`), então um card pode ser montado a partir de qualquer um deles.

---

## O Card (lista)

```json
{
  "researcher_id": "...",
  "name": "Maria Silva",
  "image": "/v2/researcher/.../image",
  "graduation": "Doutorado",
  "classification": "E+",
  "lattes_update": "2026-08-26T20:07:57",
  "affiliations": [ ... ],
  "counts": { "articles": 5, "book_chapters": 2, "books": 2, "patents": 0, "software": 0, "brands": 0 },
  "matches": null
}
```

!!! tip "Contadores pré-calculados"
    `counts` vem pronto da visão materializada, sem nenhuma consulta extra por página. Pesquisadores sem produção registrada retornam zeros.

---

## O Perfil (detalhe)

Tudo do card (exceto `matches`, que só faz sentido dentro de uma busca), mais:

```json
{
  "abstract": "...",
  "abstract_ai": "...",
  "identifiers": { "lattes_id": "...", "lattes_10_id": "...", "orcid": null, "scopus": null, "openalex": null },
  "bibliometrics": { "h_index": 7, "i10_index": 4, "cited_by_count": 120, "works_count": 30 },
  "graduate_programs": [
    { "program": { "id": "...", "name": "História", "acronym": null }, "type": "PERMANENTE" }
  ],
  "research_groups": [ { "id": "...", "name": "..." } ]
}
```

* `bibliometrics` é `null` quando o pesquisador não tem registro no OpenAlex. Um zero seria ambíguo.
* Programas seguem o mesmo padrão de [vínculos institucionais](vinculos-institucionais.md): o programa (`GraduateProgramRef`, propositalmente enxuto) fica separado do tipo de vínculo.
* Pesquisador inexistente retorna **HTTP 404**.

---

## Foto

`GET /v2/researcher/{id}/image` devolve a foto. Na primeira requisição ela é baixada do CNPq a partir do `lattes_10_id` e guardada em `storage/image_researcher`. Quando não é possível obtê-la, retorna **HTTP 404**, e o frontend deve exibir um avatar padrão.
