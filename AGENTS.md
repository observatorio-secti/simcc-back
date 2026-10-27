# AGENTS.md — SimCC Back (`simcc-back`)

Este repositório faz parte do **Ecossistema Observatório CT&I Bahia / SimCC**. Ele é versionado de forma independente e implementa a **API Pública de Busca e Inteligência Científica do SimCC (V1 e V2)**, além de ser o **dono oficial das migrações Alembic das 76 tabelas de domínio e das 15 Visões Materializadas (`mv_*`)** compartilhadas entre o `write_db` e o `read_db`.

> Consulte também a documentação conceitual em [`docs/index.md`](docs/index.md) e o guia de integração do ecossistema em `../README.md` (`Simcc/README.md`) e `../../AGENTS.md`.

---

## 1. Os 4 Pilares da Arquitetura V2 e Regras de Domínio

1. **Dono Oficial do Schema de Domínio (`migrations/`)**:
   - Todas as 76 tabelas base (`researcher`, `institution`, `bibliographic_production`, `foment`, `graduate_program`, etc.) e as 15 *Materialized Views* (`mv_researcher_search`, `mv_search_*`, `mv_canonical_*`) são gerenciadas pelas migrações Alembic deste repositório.
   - Tanto o `read_db` (`5434`) quanto o `write_db` (`5435`, usado pelo `simcc-etl`) rodam `alembic upgrade head` a partir deste repositório. Além disso, a `observatorio-maria` lê o `read_db` em modo *read-only* (`catalog/simcc.yaml`).
2. **Orçamento Rigoroso de Consultas e Visões Materializadas**:
   - Na V2 (`src/simcc/v2/`), as buscas consultam exclusivamente as *Materialized Views* indexadas com GIN (`tsvector`), mantendo um orçamento previsível de queries (2 queries na busca básica).
   - **Recursos Opt-in**: Cálculos pesados (snippets de evidências/matches e faceting disjuntivo) só executam quando explicitamente solicitados e apenas sobre os itens paginados (máximo 50 itens).
3. **Cache Geracional no Redis (`simcc:v2:search:generation`)**:
   - As buscas da V2 utilizam chaves de cache prefixadas pela geração atual no Redis (`6379`). Quando o `simcc-etl` publica novos dados no `read_db`, ele incrementa essa chave, invalidando instantaneamente o cache antigo sem precisar varrer chaves.
4. **Validação Defensiva e Estilo de Código**:
   - Parâmetros desconhecidos em filtros retornam `HTTP 422` imediatamente.
   - Estilo Ruff configurado em `pyproject.toml`: `line-length = 79` e `quote-style = 'single'`.
   - Documentação, comentários e commits em **Português do Brasil (pt-BR)**; identificadores de código em **inglês**.

---

## 2. Comandos Padrão de Desenvolvimento

- **Instalar dependências**: `poetry install`
- **Aplicar migrações Alembic**: `poetry run alembic upgrade head`
- **Iniciar servidor dev**: `poetry run task run` (`fastapi dev src/simcc --reload-dir "src/simcc"`)
- **Executar testes (sem chamadas reais de IA)**: `poetry run task test`
- **Executar testes integrados com OpenAI**: `poetry run task test_live`
- **Gerar relatório de cobertura HTML**: `poetry run task cov`
- **Servir documentação MkDocs**: `poetry run mkdocs serve`

---

## 3. Padrão de Documentação e Gatilhos Obrigatórios (Definition of Done)

A documentação deste repositório é dividida em duas camadas:
- [`README.md`](README.md): Guia técnico rápido (arquitetura V1/V2, árvore de diretórios, migrações, variáveis `.env`, comandos `taskipy` e testes).
- [`docs/`](docs/index.md) + [`mkdocs.yml`](mkdocs.yml): Portal MkDocs Material com os conceitos profundos da V2 (MVs, filtros, facets, vínculos institucionais, cache e guia de contribuição para rotinas, endpoints e testes).

### Tabela de Atualização Obrigatória

**Nenhuma alteração de código está pronta sem atualizar a documentação correspondente na mesma tarefa:**

| Se você alterar... | Atualize obrigatoriamente: |
| :--- | :--- |
| Variáveis em `src/simcc/core/settings.py` | Seção **⚙️ Configuração (`.env`)** no [`README.md`](README.md) e `../README.md` |
| Migrações em `migrations/versions/` ou estrutura das *Materialized Views* (`mv_*`) | [`README.md`](README.md), `docs/conceitos/arquitetura.md`, `../README.md` e verificar impacto em `simcc-etl` e `observatorio-maria/catalog/simcc.yaml` |
| Rotas, filtros, facetas ou regras de cache em `src/simcc/v2/` | [`README.md`](README.md) e a página correspondente em `docs/conceitos/` |
| Estrutura de pacotes em `src/simcc/` | Árvore **📁 Estrutura de Diretórios** no [`README.md`](README.md) |
