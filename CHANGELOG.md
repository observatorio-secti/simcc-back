# Changelog — Endpoints V2 de Produções e Busca

Este changelog descreve os novos endpoints desenvolvidos na API V2 do SimCC, a motivação de arquitetura, como cada um funciona e os parâmetros aceitos.

> **Nota sobre Schemas e Contratos de Retorno:**
> Para consultar os contratos completos de retorno (campos JSON, modelos Pydantic `*Summary`, `*Detail` e envelopes de paginação), consulte a documentação interativa do Swagger em `/docs` ou `/redoc`.

---

## 1. Contexto & Arquitetura de Produções Canônicas

### O Problema do Banco Legado
No banco relacional do SimCC, cada produção científica ou técnica é associada individualmente a um pesquisador (`researcher_id`). Quando múltiplos pesquisadores da mesma instituição publicam um mesmo artigo, livro, capítulo, patente ou software em coautoria, essa obra existia repetida várias vezes no banco. 

Anteriormente, para listar sem duplicatas era necessário recorrer a filtros pesados com `DISTINCT ON` ou agrupamentos lentos em tempo de execução, inviabilizando paginações consistentes e buscas textuais rápidas.

### A Solução V2: Visões Materializadas Canônicas
Implementamos visões materializadas canônicas indexadas no PostgreSQL (`mv_canonical_*`), que:
1. **Desduplicam Obras:** Agrupam registros idênticos por chaves naturais unificadas (DOI, ISBN, Código de Patente, Código de Software, ou Título normalizado sem acento + Ano).
2. **Consolidam Coautores da Casa:** Agregam todos os pesquisadores da plataforma em uma lista unificada `platform_authors: list[ResearcherRef]`.
3. **Agrupam Metadados e Resumos:** No caso de artigos, fundem os dados do OpenAlex (resumos, citações, links para PDF aberto), mesmo se o scraper tivesse vinculado a apenas um dos coautores.
4. **Busca Textual Ponderada (FTS):** Vetores `tsvector` com dicionário em português sem acentos (`pt_unaccent`), gerando automaticamente snippets de texto destacados com `<b>...</b>` (`matches`) via `ts_headline`.
5. **Índices de Alta Performance:** Índices B-Tree para anos e chaves de negócio, e GIN para arrays de pesquisadores, instituições, programas de pós-graduação e vetores de busca.

---

## 2. Endpoints de Pesquisadores (Filtros Expandidos)

### `GET /v2/researchers`
Atualização do endpoint de busca e filtragem de pesquisadores.

* **O que foi adicionado:**
  * O parâmetro `source_type` agora suporta dois novos domínios:
    * `PARTICIPATION_EVENT`: Filtra pesquisadores que possuem participações em eventos (congressos, simpósios, encontros).
    * `AREA_SPECIALTY`: Filtra pesquisadores que possuem especialidades ou áreas de atuação cadastradas.
* **Como funciona:**
  * **Sem busca textual (`q` omitido):** Avalia se o pesquisador possui registros na tabela de participação em eventos ou especialidades da área (respeitando o recorte temporal de `year_start` e `year_end` quando aplicável).
  * **Com busca textual (`q` informado):** O motor de busca restringe as evidências textuais exclusivamente ao documento de eventos ou áreas, garantindo que o pesquisador só seja retornado caso o termo buscado conste na respectiva produção/especialidade.

---

## 3. Endpoints de Produções Científicas e Tecnológicas

Todos os endpoints de listagem seguem o envelope padrão V2 (`data`, `pagination`, `filters_applied`, `sort`, `meta`) e expõem os mesmos parâmetros de controle de paginação:
* `page`: Número da página (padrão: `1`, mínimo: `1`).
* `per_page`: Quantidade de itens por página (padrão: `12`, intervalo: `1` a `100`).

---

### 3.1 Artigos Científicos

#### `GET /v2/production/article`
Listagem e busca textual avançada de artigos científicos desduplicados.

* **Como funciona:**
  * Consulta a visão `mv_canonical_articles` (mais de 142 mil artigos canônicos desduplicados).
  * Quando informado o parâmetro `q`, realiza busca ponderada por relevância (Título: Peso A, Palavras-chave: Peso B, Resumo: Peso C, Revista/ISSN: Peso D) e inclui trechos destacados do resumo ou título em `matches`.
* **Filtros disponíveis:**
  * `q` (string): Termo de busca textual.
  * `year_start` / `year_end` (int): Intervalo de ano de publicação.
  * `qualis` (list[string]): Lista de estratos Qualis (ex.: `A1`, `A2`, `B1`, etc.).
  * `researcher_id` (UUID): Artigos que possuem determinado pesquisador como coautor.
  * `institution_id` (UUID): Artigos coautorados por pesquisadores vinculados a uma instituição.
  * `graduate_program_id` (UUID): Artigos vinculados a programas de pós-graduação.
  * `has_open_access` (bool): Apenas artigos com PDF ou acesso aberto disponível.
* **Ordenação (`by` e `order`):**
  * `by`: `relevance` (quando `q` presente), `year` (padrão), `citations`, `title`.
  * `order`: `asc` ou `desc`.

#### `GET /v2/production/article/{article_id:path}`
Dossiê detalhado do artigo.

* **Como funciona:**
  * Resolução flexível de chave: o parâmetro `article_id` aceita tanto o UUID canônico, qualquer UUID legado das produções originais que foram fundidas, ou diretamente o **DOI** (mesmo contendo barras, ex.: `10.1016/j.procs.2020.04.123`).
  * Retorna o artigo completo com abstract na íntegra, métricas de citação, links externos (PDF e landing page) e a lista de coautores da casa (`platform_authors`).

---

### 3.2 Livros

#### `GET /v2/production/book`
Listagem e busca de livros publicados desduplicados.

* **Como funciona:**
  * Consulta `mv_canonical_books` (quase 20 mil livros canônicos).
  * FTS ponderado: Título (Peso A), Editora e Cidade (Peso B), ISBN (Peso C).
* **Filtros disponíveis:**
  * `q` (string): Termo de busca.
  * `year_start` / `year_end` (int): Intervalo de ano.
  * `researcher_id` / `institution_id` / `graduate_program_id` (UUID): Filtros de autoria e vínculo institucional.
* **Ordenação (`by` e `order`):**
  * `by`: `relevance`, `year`, `title`.
  * `order`: `asc`, `desc`.

#### `GET /v2/production/book/{book_id:path}`
Consulta detalhada de um livro.

* **Como funciona:**
  * Resolução flexível por UUID (canônico ou legado) ou pelo número do **ISBN** (ex.: `978-85-1234-567-8`).
  * Retorna os metadados editoriais completos (editora, cidade, número de páginas, volume, coautores da plataforma).

---

### 3.3 Capítulos de Livros

#### `GET /v2/production/book-chapter`
Listagem e busca de capítulos de livros desduplicados.

* **Como funciona:**
  * Consulta `mv_canonical_book_chapters` (mais de 60 mil capítulos canônicos).
  * FTS ponderado: Título do capítulo (Peso A), Título do livro (Peso B), Editora/Organizadores (Peso C), ISBN (Peso D).
* **Filtros disponíveis:**
  * `q` (string): Termo de busca.
  * `year_start` / `year_end` (int): Intervalo de ano.
  * `researcher_id` / `institution_id` / `graduate_program_id` (UUID).
* **Ordenação (`by` e `order`):**
  * `by`: `relevance`, `year`, `title`.
  * `order`: `asc`, `desc`.

#### `GET /v2/production/book-chapter/{chapter_id:path}`
Consulta detalhada de um capítulo de livro.

* **Como funciona:**
  * Resolução por UUID ou por **ISBN**.
  * Retorna dados completos do capítulo (título da obra coletiva, organizadores, páginas inicial e final, editora e coautores).

---

### 3.4 Softwares

#### `GET /v2/production/software`
Listagem e busca de softwares e programas de computador desenvolvidos.

* **Como funciona:**
  * Consulta `mv_canonical_software`.
  * FTS ponderado: Nome/Título do software (Peso A), Plataforma e Ambiente operacional (Peso B), Código do registro (Peso C).
* **Filtros disponíveis:**
  * `q` (string): Termo de busca.
  * `year_start` / `year_end` (int): Intervalo de ano.
  * `researcher_id` / `institution_id` / `graduate_program_id` (UUID).
* **Ordenação (`by` e `order`):**
  * `by`: `relevance`, `year`, `title`.
  * `order`: `asc`, `desc`.

#### `GET /v2/production/software/{software_id:path}`
Consulta detalhada de um software.

* **Como funciona:**
  * Resolução por UUID ou pelo **código de registro/depósito** (ex.: `SW-2024-TEST-99`).
  * Retorna plataforma tecnológica, ambiente de execução, disponibilidade, entidade financiadora e desenvolvedores da plataforma.

---

### 3.5 Patentes

#### `GET /v2/production/patent`
Listagem e busca de patentes registradas ou concedidas.

* **Como funciona:**
  * Consulta `mv_canonical_patents` (unificando inventores da instituição).
  * FTS ponderado: Título da invenção (Peso A), Categoria e Detalhes técnicos (Peso B), Código de depósito (Peso C).
* **Filtros disponíveis:**
  * `q` (string): Termo de busca.
  * `year_start` / `year_end` (int): Intervalo de ano de concessão/depósito.
  * `researcher_id` / `institution_id` / `graduate_program_id` (UUID).
* **Ordenação (`by` e `order`):**
  * `by`: `relevance`, `year`, `title`.
  * `order`: `asc`, `desc`.

#### `GET /v2/production/patent/{patent_id:path}`
Consulta detalhada de uma patente.

* **Como funciona:**
  * Resolução por UUID ou pelo **número do processo/código** (ex.: `BR 10 2024 000123 4`).
  * Retorna dados de concessão, depósito, detalhes técnicos, categoria e inventores vinculados à instituição.

---

### 3.6 Participação em Eventos

#### `GET /v2/production/event`
Listagem e busca de participações em congressos, simpósios, feiras e encontros.

* **Como funciona:**
  * Consulta `mv_canonical_events` (mais de 479 mil participações canônicas desduplicadas).
  * FTS ponderado: Título do trabalho apresentado (Peso A), Nome do Evento (Peso B), Natureza e Forma/Tipo de participação (Peso C).
* **Filtros disponíveis:**
  * `q` (string): Termo de busca.
  * `year_start` / `year_end` (int): Ano do evento.
  * `researcher_id` / `institution_id` / `graduate_program_id` (UUID).
* **Ordenação (`by` e `order`):**
  * `by`: `relevance`, `year`, `title`.
  * `order`: `asc`, `desc`.

#### `GET /v2/production/event/{event_id:path}`
Consulta detalhada de uma participação em evento.

* **Como funciona:**
  * Resolução por UUID.
  * Retorna nome do evento, natureza (nacional, internacional), tipo de participação (convidado, apresentador, participante) e forma de apresentação (oral, pôster).

---

## 4. Tabela Resumo dos Endpoints Criados

| Endpoint | Método | Descrição | Resolução Chave de Detalhe |
| :--- | :---: | :--- | :--- |
| `/v2/researchers` | `GET` | Busca e filtros com novos tipos `PARTICIPATION_EVENT` e `AREA_SPECIALTY` | - |
| `/v2/production/article` | `GET` | Listagem e busca FTS de artigos científicos | - |
| `/v2/production/article/{id}` | `GET` | Detalhe completo de artigo científico | UUID ou DOI |
| `/v2/production/book` | `GET` | Listagem e busca FTS de livros | - |
| `/v2/production/book/{id}` | `GET` | Detalhe completo de livro | UUID ou ISBN |
| `/v2/production/book-chapter` | `GET` | Listagem e busca FTS de capítulos de livros | - |
| `/v2/production/book-chapter/{id}` | `GET` | Detalhe completo de capítulo de livro | UUID ou ISBN |
| `/v2/production/software` | `GET` | Listagem e busca FTS de softwares | - |
| `/v2/production/software/{id}` | `GET` | Detalhe completo de software | UUID ou Código |
| `/v2/production/patent` | `GET` | Listagem e busca FTS de patentes | - |
| `/v2/production/patent/{id}` | `GET` | Detalhe completo de patente | UUID ou Código |
| `/v2/production/event` | `GET` | Listagem e busca FTS de participações em eventos | - |
| `/v2/production/event/{id}` | `GET` | Detalhe completo de participação em evento | UUID |
