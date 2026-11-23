# Changelog da API v2

O contrato publicado é o `/v2/openapi.json`, versionado em [`openapi-v2.json`](openapi-v2.json). Os tipos do front devem ser gerados a partir dele, e não do `/openapi.json` mesclado (V1 + V2), que sobrescreve componentes de mesmo nome.

Toda mudança de contrato altera esse arquivo e aparece no diff do PR (teste `tests/v2/unit/test_openapi_contract.py`).

## 2026-11-20 — Fases 0, 1 e 2 (branch `feat/v2-contrato`)

### Mudanças que quebram o front atual

Precisam ser publicadas junto com a versão do front que as consome.

| Onde | Antes | Agora | Ajuste no front |
| --- | --- | --- | --- |
| Rotas de detalhe (`/v2/production/{kind}/{id}`, `/v2/researcher/{id}`) | Objeto solto | `{ data, meta }` | Ler `body.data` |
| Erros | `{ detail: "..." }` ou `{ detail: [...] }` | `{ error: { code, message, details[] } }` | Ler `error.code` e `error.message` |
| Tipos de produção em `source_type`, `matches.by_type`, `matches.items[].source_type`, faceta `source_type` e `/v2/suggestion` | `ARTICLE`, `BOOK_CHAPTER`, `PARTICIPATION_EVENT`, `AREA_SPECIALTY`, `PROFILE`... | `article`, `book_chapter`, `event`, `area_specialty`, `profile`... | Comparar com os valores novos. Na entrada, os antigos continuam aceitos |
| Trecho destacado (`matches[].snippet` em pesquisadores e produções) | Texto com `[[termo]]` ou `<b>termo</b>` | Texto puro + `highlights: [início, fim)[]` em unidades UTF-16 | `snippet.slice(início, fim)` |
| `magazine.qualis` em artigos | Texto livre (`A1`, `SQ`, `NP`, `None`) | Enum `A1`…`C` ou `null`, mais `qualis_status` (`not_rated`, `not_applicable`) | Exibir `qualis_status` quando `qualis` for `null` |
| `magazine.jcr` em artigos | `string` | `number \| null` | — |
| Faceta e filtro `qualis` em artigos | Valores do banco (`SQ`, `NP`...) | `A1`…`C`, `not_rated`, `not_applicable` | `SQ`/`NP` ainda aceitos na entrada |
| `ArticleDetail.keywords` | `string` | `string[]` | — |
| `/v2/researcher` | Campo `summary` (sempre `null`) | Removido | — |
| `/v2/analytics` | `data[].date` em `YYYYMMDD` | ISO (`2026-11-20`) e `meta` | — |

### Campos obsoletos (`deprecated`), removidos na virada

| Campo | Use no lugar |
| --- | --- |
| `researcher_id` em `ResearcherSummary`/`ResearcherDetail` | `id` |
| `image` (caminho relativo) | `image_url` (URL absoluta) |
| Parâmetros `by` e `order` em `/v2/production/*` | `sort_by` e `sort_order` |
| Caminho `/v2/graduate_program` | `/v2/graduate-program` |

### Acréscimos (não quebram)

- `meta.data_as_of` passa a vir preenchido. Antes saía sempre `null` em produção, porque o valor ficava só na memória de um processo que nunca fazia refresh.
- `param` em cada faceta: o nome do filtro correspondente (`institution` → `institution_id`; `year` → `["year_start", "year_end"]`).
- `/v2/institution`: `meta`, `sort`, `filters_applied`, `sort_by`/`sort_order` e detalhe `/v2/institution/{id}` com contagens.
- `/v2/graduate-program`: filtros `institution_id`, `area`, `modality`, `rating`, `state`, `city`; facetas desses campos; item com área, modalidade e conceito; detalhe com linhas de pesquisa e instituição.
- Novos tipos de produção, com lista, detalhe, facetas e os filtros comuns: `/v2/production/brand` (filtro `nature`), `/v2/production/guidance` (`nature`, `type`, `status`) e `/v2/production/report`.
- `/v2/researcher`: filtro `researcher_id`; `counts.guidance` e `counts.reports`.
- `/v2/researcher/{id}?include=education,experience,foment`: formação, experiência profissional e bolsas.
- `authors: { name }[]` em artigos, livros e capítulos, separados de `all_authors_raw` (sem casar com pesquisadores; esses continuam em `platform_authors`).
- `/v2/magazine` e `/v2/magazine/{id}`: busca por nome, filtros `issn` e `qualis`, ordenação por nome ou JCR, faceta `qualis`.
- `/v2/scholarship`: bolsas e auxílios, com filtros `researcher_id`, `institution_id`, `graduate_program_id`, `modality`, `category_level` e facetas.
- `/v2/researcher/{id}/terms`: palavras mais frequentes nos títulos das produções (nuvem de palavras).
- `/v2/metrics/production/{kind}`: série anual `{ period, value }[]` com os mesmos filtros de `/v2/production/{kind}`.
- Exemplos no OpenAPI para `meta`, erro, paginação, faceta e evidência.

### Operação

- Novas MVs: `mv_canonical_brands`, `mv_canonical_guidance`, `mv_canonical_reports` (migração `a1c4e7f2b9d3`). **A rotina de refresh do ETL precisa incluí-las**, na ordem de `SEARCH_MATERIALIZED_VIEWS` (`src/simcc/v2/services/mv_refresh_service.py`), e gravar `mv_refresh_metadata`, de onde sai o `data_as_of`.
- O cache de busca no Redis mudou de versão (`SCHEMA_VERSION = 4`): as entradas antigas deixam de ser lidas no deploy, sem limpeza manual.
- CI: os testes rodam também em PR para `develop` e `main`; o deploy roda só em push na `main`.

## 2026-11-22 — Agrupamento (`group_by`) em `/v2/metrics/production/{kind}`

### Acréscimos (não quebram)

- `/v2/metrics/production/{kind}` passa a aceitar o query param opcional `group_by`:
  - `article`: `qualis` (`A1`…`C`, `not_rated`, `not_applicable`)
  - `guidance`: `nature`, `status`
  - `event`: `nature`, `type_participation`
  - `research-project`: `status`, `nature` (usando `start_year` como `period`)
- Quando `group_by` é informado, `ProductionMetricResponse` inclui `group_by` e cada item de `data` inclui `groups` (`Record<string, number>`, omitindo chaves com contagem `0`). Quando omitido, o payload permanece idêntico ao contrato anterior.
- `/v2/metrics/production/{kind}` passa a aceitar os filtros específicos de cada `{kind}` já existentes em `/v2/production/{kind}` (ex.: `qualis` em `article`, `nature` e `status` em `guidance`).

## 2026-11-23 — Métricas gerais (`/v2/metrics/general`)

### Acréscimos (não quebram)

- `GET /v2/metrics/general`: retorna as contagens únicas de produções (`articles`, `books`, `book_chapters`, `work_in_event`, `patents`, `software`, `brands`) a partir das MVs canônicas e o total de pesquisadores (`researchers`), no envelope `{ data, meta }` com cache Redis (`SearchCacheDep`).
