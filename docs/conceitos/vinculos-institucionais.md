# Vínculos Institucionais

Cada pesquisador retornado por `GET /v2/researcher` traz a lista `affiliations`, com todas as instituições às quais ele está vinculado.

---

## Instituição vs. Vínculo

Alguns dados descrevem **a instituição** (nome, sigla, logo). Outros descrevem **a relação do pesquisador com ela** (regime de trabalho, território de identidade, cidade). A mesma UFBA pode ter um pesquisador com 40h e outro com 20h.

Por isso a resposta usa **composição**: o objeto `institution` é sempre o mesmo `InstitutionRef` devolvido por `GET /v2/institution`, e os atributos do vínculo ficam um nível acima.

```json
{
  "researcher_id": "...",
  "name": "Maria Silva",
  "affiliations": [
    {
      "institution": {
        "id": "...",
        "name": "Universidade Federal da Bahia",
        "acronym": "UFBA",
        "image": "/storage/institutions/picture/UFBA.png",
        "cover": "/storage/institutions/covers/UFBA.jpg"
      },
      "workload": 40,
      "identity_territory": "Metropolitano de Salvador",
      "city": { "id": "...", "name": "Salvador" }
    }
  ]
}
```

!!! tip "Um único formato de instituição"
    O frontend pode usar o mesmo tipo e o mesmo componente para exibir uma instituição, venha ela do catálogo ou de um vínculo. Nunca adicione campos do vínculo dentro de `InstitutionRef`.

---

## Origem dos Dados

* Os vínculos vêm **exclusivamente** da tabela `researcher_institution`. A coluna legada `researcher.institution_id` não é considerada.
* `image` e `cover` são resolvidos pela sigla em `storage/institutions/picture` e `storage/institutions/covers`. Quando não há logo em disco, `image` usa a coluna `institution.image`.
* As URLs das imagens ficam em cache por processo: um arquivo novo só aparece após reiniciar o servidor.
* Os vínculos são buscados em **uma única consulta** para todos os pesquisadores da página, e a lista vem ordenada pelo nome da instituição.
