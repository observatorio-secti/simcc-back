# Resposta do backend aos pedidos de contrato v2

_Atualizado em 2026-11-20 (respostas do front incorporadas; Fases 0, 1 e 2 implementadas na branch `feat/v2-contrato`, ver [changelog-v2.md](changelog-v2.md))_

A maior parte dos pedidos é viável e alinhada com o rumo da V2; vários já existem e o documento do front está desatualizado nesses pontos. O que exige cuidado são as renomeações de campos e o novo formato de detalhe, que quebram o front atual e precisam de transição. Autenticação, IdP, ETL e grupos de pesquisa não são responsabilidade deste repositório.

> **Avisos de escopo**
>
> - **Dados da UFMG foram descontinuados.** As rotas `ufmg/researcher`, `ufmg/technician` e os campos específicos da UFMG (`dep_nom`, `entradanaufmg`, `menagers` etc.) não terão equivalente na V2 e não devem ser consumidos pelo novo front.
> - **Grupos de pesquisa não são responsabilidade deste repositório.** O que existe hoje sobre grupos aqui não será modificado nem ampliado; o novo front deve continuar usando a API ODA para grupos.
> - **Exportação CSV (`format=csv`) fica de fora no momento.** O custo e o risco de carga não compensam agora; o front continua gerando o CSV a partir da página carregada.

## 1. Já existe na V2

Estes pontos do pedido já estão atendidos no código atual (branch `develop`). Vale o front revisar o documento antes de planejar em cima deles.

| Pedido | Situação hoje | Onde |
| --- | --- | --- |
| OpenAPI 3.1 publicado e versionado com o código | Gerado pelo FastAPI a partir dos schemas em `/v2/openapi.json` (só V2) e `/openapi.json` (V1+V2 mesclados). O front deve consumir só o `/v2/openapi.json`: o mesclado sobrescreve componentes de mesmo nome | `src/simcc/__init__.py` |
| `GET /v2/researcher/{id}` | Existe: identificadores, bibliometria (OpenAlex), vínculos, programas, grupos e contagens. Faltam formação, experiência e fomento | `v2/routers/researcher.py` |
| Facetas em produções | Todas as listagens `/v2/production/{kind}` aceitam `facets` e devolvem o mesmo `FacetResult` de pesquisadores: `institution`, `graduate_program`, `city`, `identity_territory`, `year`, `area` + facetas próprias do tipo (ex.: `qualis` em artigos) | `production_search_service.py`, `production_facets_repo.py` |
| `researcher_id` como filtro de produção | Aceito em todos os tipos (lista repetida) | `ProductionBaseFilter` |
| `/v2/institution` e `/v2/graduate_program` | Existem como catálogo (busca `q` + paginação). Sem detalhe, facetas e `meta` | `v2/routers/institution.py`, `graduate_program.py` |
| URL da imagem no payload | Campo `image` já vem em cada pesquisador (`/v2/researcher/{id}/image`, busca por id, não por nome). Hoje é relativa | `schemas/researcher.py` |
| Datas e ano tipados | `lattes_update` é `datetime` e `year` é `int \| null` na V2 | schemas V2 |
| Enums de entrada | `sort_by`, `source_type`, `classification` já são `Literal` e saem como enum no OpenAPI | `schemas/filters.py`, `params.py` |
| `per_page` máximo e `total_items` | Máximo 100 documentado; `total_items` é contagem exata (`count`) | `PaginationParams` |
| 404 × lista vazia | Detalhe inexistente devolve 404; busca sem resultado devolve `data: []` com 200; parâmetro desconhecido devolve 422 | services V2 |

Os campos com nome em português ou abreviado citados no pedido (`dep_nom`, `entradanaufmg`, `menagers`) existem só na V1 e pertencem aos dados da UFMG, que foram descontinuados. A V2 já segue inglês e snake_case.

## 2. Convenções gerais

Todas são válidas. As que só acrescentam campos entram sem risco; as que renomeiam ou removem quebram o front atual e precisam de um período com os dois formatos.

| Tema | Veredito | Como faremos | Quebra o front atual? |
| --- | --- | --- | --- |
| `id` em toda entidade | Aceito | Adicionar `id` em `ResearcherSummary`/`Detail` e manter `researcher_id` marcado como `deprecated` no OpenAPI até o front antigo sair | Não, se feito em duas etapas |
| Enum único de tipo de produção (`book_chapter`) | Aceito | Um enum `ProductionKind` em snake_case para filtro, faceta, `matches` e sugestão. A entrada aceita os valores antigos como alias (já fazemos isso com `EVENT` → `PARTICIPATION_EVENT`). O valor no banco (`research_dictionary.type_`, MVs) não muda: a tradução fica na camada de schema | Sim na saída; transição necessária |
| Trecho destacado como texto + intervalos | Aceito, recomendamos | Hoje: `[[ ]]` em pesquisador (`researcher_repo.py`) e `<b>` em produções (`article_repo.py`, `production_repo.py`). O `ts_headline` passa a usar marcadores Unicode de uso privado, que o Python remove e converte em `[início, fim]`. Unidade proposta: UTF-16, que é o que `String.slice` do JS usa | Sim; campo novo (`highlights`) ao lado do antigo durante a transição |
| Datas ISO 8601 | Aceito | Só `/v2/analytics` ainda devolve `YYYYMMDD` (vem do GA4); converter na saída | Só analytics |
| Contagens como `number` | Já atendido na V2 | O problema citado (`scholarship_quantity`) é da V1 | Não |
| Qualis como enum fechado | Aceito com ressalva | O banco guarda `SQ` como padrão e tem `None`/`NP`. Saída: `qualis: A1…C \| null` e `qualis_status` separado. O filtro e a faceta `qualis` usam os mesmos valores, então mudam juntos | Sim; afeta filtro, faceta e cache |
| JCR como `number` | Aceito | Coluna é `String`; converter com parse tolerante (vírgula decimal), valor inválido vira `null` | Sim, tipo muda |
| `authors[]` e `keywords[]` | Parcial | `keywords[]`: viável (split do texto do OpenAlex). `authors[]`: o `all_authors_raw` é texto livre do Lattes; o split por `;` é heurístico e não dá para garantir `researcher_id` por autor sem casar nomes. Proposta: `authors: { name }[]` + o `platform_authors` que já existe (com `id`) | Não, são campos novos |
| `image_url` absoluta | Aceito | Renomear `image` → `image_url` e montar com `Settings.URL` | Sim na renomeação |
| Ausência sempre `null` | Aceito | Um `BaseModel` comum da V2 com validador que troca `''` e `'None'` por `null` em todo campo texto | Raramente |
| Nomes em inglês, sem abreviação | Já atendido na V2 | Os exemplos citados são da V1 e dos dados UFMG, descontinuados | Não |

A "API administrativa" citada no pedido não está neste repositório; as divergências dela precisam ser tratadas pelo time responsável.

## 3. Envelope de resposta e erros

Os três formatos (lista, detalhe, erro) são viáveis e baratos. O único que quebra contrato é embrulhar o detalhe em `{ data, meta }`.

| Rota | Tem hoje | Falta |
| --- | --- | --- |
| `/v2/researcher` | `data`, `pagination`, `sort`, `filters_applied`, `facets`, `meta`, `summary` | Remover `summary` (sempre `null`, tipado como `dict[str, Any]`) |
| `/v2/production/{kind}` | Mesmos campos, menos `summary` | Nada no envelope; ver ordenação na seção 4 |
| `/v2/suggestion` | `data`, `meta` | `pagination` não faz sentido em autocomplete com `limit`. Propomos declarar um formato "lista curta" sem paginação |
| `/v2/analytics` | `data`, `summary` | `meta`; `summary` já é tipado (`AnalyticsSummary`) e pode ficar |
| `/v2/institution`, `/v2/graduate_program` | `data`, `pagination` | `meta`, `sort`, `filters_applied`, `facets` |
| Rotas de detalhe | Objeto solto | `{ data, meta }`. **Quebra** quem consome o detalhe hoje |
| Erros | Padrão do FastAPI: `{ "detail": "..." }` ou `{ "detail": [...] }` no 422 | Handler global no `v2_app` para `{ error: { code, message, details[] } }`. Não afeta a V1 |

**Bug encontrado: `meta.data_as_of` sai sempre `null` em produção.** O valor vem de uma variável em memória (`MVRefreshState`) que só é preenchida por `refresh_search_materialized_views`, e nenhuma rota da API chama essa função; além disso a API roda com 4 workers, cada um com sua memória. A tabela `mv_refresh_metadata` já guarda `refreshed_at` por MV: basta ler o `max(refreshed_at)` dela (com cache curto). Falta confirmar que a rotina de refresh do ETL grava nessa tabela.

`filters_applied` já é tipado (é o próprio model de filtro da rota). Se o front vê `unknown`, é o `summary` ou um gerador lendo o `/openapi.json` mesclado.

## 4. Busca, filtros e paginação

O vocabulário comum é viável e quase todo já existe. Há uma divergência que o pedido não citou: as produções usam `by` e `order` como parâmetros de ordenação, enquanto pesquisadores usam `sort_by` e `sort_order`.

| Pedido | Veredito | Observação |
| --- | --- | --- |
| `q`, `page`, `per_page`, `sort_by`, `sort_order`, `facets`, `facet_limit` em toda listagem | Aceito | Pesquisadores já têm todos. Produções: renomear `by`/`order` para `sort_by`/`sort_order`, aceitando os nomes antigos como alias. Catálogos (instituição, programa): faltam ordenação e facetas |
| Listas como chave repetida | Já é assim; documentar | Exceções: `facets`, `include` e `collection` também aceitam vírgula (e `;` em `collection`). Manter por compatibilidade, documentar a forma repetida como oficial |
| Mesmos nomes de filtro | Aceito, exceto `research_group_id` | Falta `researcher_id` em pesquisadores. **`research_group_id` não será oferecido por esta API**, já que grupos de pesquisa não são responsabilidade deste repositório |
| Chave da faceta = nome do filtro | Aceito via campo `param` | As facetas se chamam `institution`, `city`, `year` e os filtros `institution_id`, `city_id`, `year_start`/`year_end`. Recomendamos acrescentar `param` em cada `FacetResult` (não quebra nada) em vez de renomear chaves. A faceta `year` mapeia para um intervalo, não 1:1 |
| `sort_by` como enum por rota | Já atendido | `Literal` em `SortParams`, `ArticleSort`, `ProductionSort` |
| `per_page` máximo e `total_items` exato | Já atendido | Máximo 100; contagem exata |
| Exportação `format=csv` | **Fora do escopo no momento** | É o pedido com mais risco operacional: sem `per_page`, uma busca ampla varre a MV inteira. Recomendamos deixar a exportação de fora agora e manter o CSV montado no front a partir da página carregada. Se voltar à pauta, precisará de `StreamingResponse`, teto de linhas, nenhuma faceta e regras de achatamento por entidade |

## 5. Cobertura da V2

Todas as entidades sob responsabilidade deste repositório têm tabela no banco, então nada é inviável tecnicamente. O custo vem de criar MVs novas, não das rotas em si.

| Prioridade | Entidade | Situação na V2 | Custo | Observação |
| --- | --- | --- | --- | --- |
| 1 | Pesquisador (detalhe) | Rota existe | Baixo | Acrescentar formação (`education`), experiência (`researcher_professional_experience`) e fomento (`foment`). Sugerimos `include=education,experience,foment` para não pesar o detalhe padrão. O campo `research_groups` atual fica como está, sem evolução |
| 1 | Produções por pesquisador | `article`, `book`, `book-chapter`, `software`, `patent`, `event`, `research-project` já aceitam `researcher_id` | Médio a alto | **Implementado:** `brand`, `guidance` e `report` (relatório técnico, `research_report`), cada um com MV canônica. `technical` saiu do pedido: o front não usa os ~15 tipos técnicos do banco |
| 1 | Instituição | Lista existe | Baixo | Falta detalhe `/{id}`, facetas e `meta` |
| 1 | Programa de pós | Lista existe em `/v2/graduate_program` | Baixo | Falta detalhe com linhas de pesquisa (`research_lines_programs`). Produções pelo filtro `graduate_program_id` já funcionam |
| 1 | Grupo de pesquisa | **Fora do escopo** | — | Não é responsabilidade deste repositório. O que existe aqui não será modificado; o front continua na API ODA |
| 2 | Revista | Não existe | Baixo | `periodical_magazine` + `jcr`; Qualis e JCR tipados como na seção 2 |
| 2 | Indicadores | Não existe | Alto | ~15 consultas pesadas da V1 (`metrics_query.py`). Migrar um indicador por vez para `/v2/metrics/{indicador}`, mantendo a V1 até cada um estar pronto |
| 2 | Bolsistas | Não existe | Médio | Base em `foment`; o filtro `modality` já existe em pesquisadores |
| 2 | Nuvem de palavras | Não existe | Baixo | `research_dictionary` e áreas; preferimos rota `/v2/researcher/{id}/terms` a uma faceta |
| 3 | MarIA | Não existe | Alto | Já há `pgvector` e `ai_search_documents`; depende de custo de embeddings e latência |
| 3 | Rotas UFMG | **Descontinuadas** | — | Os dados da UFMG foram descontinuados. Não haverá rota na V2 nem extensão do modelo comum; o novo front não deve consumir `ufmg/researcher` nem `ufmg/technician` |
| 3 | Recentes e newsletter | Não existe | Médio | `sort_by=created_at` exige a coluna nas MVs canônicas; falta verificar se a data de entrada está disponível na origem |

Nomes de rota: hífen nos caminhos e snake_case em campos e enums, confirmado pelo front. `/v2/graduate-program` é o caminho oficial; `/v2/graduate_program` continua como alias fora do OpenAPI.

## 6. Autenticação, sessão e ETL

Esta API (`simcc-back`) não tem autenticação: é pública e só de leitura. IdP, ETL e API administrativa são outros serviços, então esta seção é um parecer, não um compromisso deste repositório.

- **Chave do ETL exposta: concordamos, e é urgente.** Toda variável `VITE_*` vai para o bundle público, então qualquer visitante pode disparar rotinas do ETL. A chave deve ser trocada já, independente da refatoração; validar o token do IdP com escopo `console:etl` é a solução certa.
- **Refresh token em cookie `httpOnly`, `/me` com escopos, 401 × 403:** válidos; dependem do time do IdP.
- **CORS:** aqui está `allow_origins=['*']` com `allow_credentials=True`. Para uma API pública sem cookie isso funciona, mas se algum dia ela aceitar cookie ou token, a lista de origens precisa ser fechada.
- **Se a V2 passar a ter dados restritos** (coleções, buscas salvas), será preciso validar o JWT do IdP aqui (JWKS) e separar o cache Redis por usuário. Hoje a chave de cache não considera usuário.

## 7. O que pode quebrar o backend

Nenhum pedido exige mudar a arquitetura (routers → services → repositories sobre MVs). Os riscos são de compatibilidade e de carga.

1. **Renomeações quebram o front atual.** `researcher_id` → `id`, `image` → `image_url`, enums de tipo, Qualis, JCR e o formato do destaque mudam a saída. Proposta: acrescentar o campo novo, marcar o antigo como `deprecated` no OpenAPI e remover só quando o front antigo sair do ar.
2. **Detalhe em `{ data, meta }`.** O front atual só usa `GET /v2/production/{kind}/{id}`, e a adaptação é de uma linha (`data.data`). Por isso entrou já na Fase 0, para ser publicado junto com o front.
3. **Novas MVs e colunas** (`mv_canonical_brands`, `mv_canonical_guidance`, `mv_canonical_reports`; `created_at` fica para a Fase 3). Cada uma é migração Alembic + refresh mais longo. A lista `SEARCH_MATERIALIZED_VIEWS` precisa ficar em sincronia com a rotina de refresh do ETL, que está em outro repositório.
4. **Qualis fechado** muda valores de filtro e faceta; o cache Redis deve ser invalidado no deploy (incrementar a geração do `SearchCache`).
5. **CSV sem limite** pode derrubar a API. Por isso a exportação fica fora do escopo no momento.
6. **Rotas legadas não podem ser desligadas em bloco.** A V1 também serve o Power BI (`/powerBi`) e integrações externas, e está montada na raiz `/`. Desligamos só as rotas que o front deixar de usar.

Sobre a validação do contrato na CI: o FastAPI já valida cada resposta contra o `response_model` (divergência vira erro 500). O que falta é (a) testes que exercitem as rotas com o schema, por exemplo com Schemathesis, e (b) um diff do `openapi.json` entre versões (ex.: `oasdiff`) que falhe a CI em mudança que quebra. Hoje a CI só roda em push para `main`; vale rodar também em PR para `develop`.

## 8. Proposta de fases

A ordem prioriza o que destrava o front sem quebrar o que está no ar.

1. **Fase 0 — correções e acréscimos sem quebra.** Corrigir `data_as_of`; handler de erro padrão na V2; `meta` em analytics e catálogos; `param` nas facetas; `id` ao lado de `researcher_id`; `image_url` absoluta ao lado de `image`; `sort_by`/`sort_order` nas produções com alias; normalização para `null`; remover `summary`. Em paralelo, o time do ETL troca a chave exposta.
2. **Fase 1 — cobertura P1.** Detalhe do pesquisador completo; detalhe de instituição e programa; `brand` e `guidance`; destaque com intervalos; enum único de tipo com aliases.
3. **Fase 2 — contrato e P2.** Exemplos por rota no OpenAPI; Schemathesis e diff de contrato na CI; revista, bolsistas, termos; Qualis e JCR tipados; primeiros indicadores.
4. **Fase 3 — virada.** Remover os campos `deprecated` (`researcher_id`, `image`) na mesma data em que o novo front for ao ar; MarIA e recentes; desligar as rotas V1 que o front deixou de usar.

Prazos dependem de equipe e não estão neste documento; a Fase 0 é a mais curta.

## 9. Perguntas em aberto: posição do backend

| Pergunta do front | Posição do backend |
| --- | --- |
| Área pública diferente para quem está logado? | Preferimos que não. Esta API não tem autenticação e o cache não considera usuário; dados por usuário ficariam melhor numa rota autenticada separada |
| Grupos saem da ODA para a V2? | **Não.** Grupos de pesquisa não são responsabilidade deste repositório e o que existe aqui não será modificado. O front continua usando a ODA |
| IdP emite refresh em cookie `httpOnly`? | Fora deste repositório; time do IdP |
| ETL fica em `simcc.uesc.br`? | Fora deste repositório; time do ETL |
| Prazo do OpenAPI da V2? | Já publicado em `/v2/openapi.json`. Exemplos e descrições completas entram na Fase 2 |
| Data de desligamento das legadas? | Por rota, não em bloco; a V1 continua servindo Power BI e integrações. As rotas UFMG estão descontinuadas |
| Formato do trecho destacado? | Texto puro + intervalos `[início, fim]` em unidades UTF-16 |

Perguntas do backend para o front:

- [x] Quais tipos entram em `technical`? **Nenhum.** O pedido passa a ser `brand` + `report`.
- [x] O front atual consome as rotas de detalhe da V2 hoje? **Só `GET /v2/production/{kind}/{id}`.** O `{ data, meta }` entrou na Fase 0.
- [x] Os caminhos com hífen servem? **Sim.**
