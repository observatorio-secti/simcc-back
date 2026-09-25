# 2. Criação de Endpoints

Os endpoints da V2 são desenvolvidos com **FastAPI** e seguem uma estrutura padronizada para manter a API previsível, bem documentada e segura.

---

## O Ciclo de Desenvolvimento de um Endpoint

Criar um novo endpoint no SIMCC V2 envolve 4 passos bem definidos:

```
1. Schemas (Pydantic) ──► 2. Repository (SQL) ──► 3. Service (Negócio) ──► 4. Router (FastAPI)
```

### 1. Definir os Schemas (`src/simcc/v2/schemas/`)
Crie os modelos de entrada (filtros) e de saída (respostas da API).
* Use `Field(description="...")` em cada atributo para que o Swagger (`/swagger`) seja autoexplicativo.
* Para listagens, reutilize os esquemas existentes de paginação ([`PaginationParams`](file:///home/jaspion/Observatorio/Simcc/simcc-back/src/simcc/v2/schemas/params.py#L13)) e ordenação ([`SortParams`](file:///home/jaspion/Observatorio/Simcc/simcc-back/src/simcc/v2/schemas/params.py#L18)).

### 2. Implementar o Repositório (`src/simcc/v2/repositories/`)
Construa as consultas utilizando SQLAlchemy:
* Separe a contagem de registros (`SELECT count(...)`) da seleção paginada (`SELECT ... LIMIT :per_page OFFSET :offset`).
* Reutilize a mesma lista de condições `WHERE` para a contagem e para a busca.

### 3. Implementar o Serviço (`src/simcc/v2/services/`)
Orquestre a chamada:
* Meça o tempo de execução (`took_ms`).
* Calcule metadados de paginação (`total_pages`, `has_next`, `has_prev`).
* Aplique validações de consistência (ex.: se o filtro `year_start` for maior que `year_end`, devolva 422).

### 4. Criar o Roteador (`src/simcc/v2/routers/`)
Crie a função de rota e vincule ao aplicativo:
* Defina explicitamente o `response_model`.
* Injete a sessão assíncrona do banco (`session: AsyncSession`).
* Registre o roteador em `src/simcc/v2/app.py`.

---

## Catálogos vs. Endpoints Complexos

Na V2 temos dois tipos principais de endpoints:

| Tipo | Exemplo | Finalidade |
|---|---|---|
| **Catálogo Simples** | `GET /v2/institution`, `GET /v2/graduate_program` | Devolve listas rápidas para caixas de seleção, autocomplete ou dropdowns do frontend. |
| **Recurso Composto** | `GET /v2/researcher` | Busca de alto desempenho com busca textual, múltiplos filtros combinados, facets e evidências. |

---

## Checklist para Criação de Endpoints

Antes de abrir um Pull Request com um novo endpoint, verifique cada item:

- [ ] **Esquema Pydantic definido:** O formato de resposta possui um modelo em `schemas/` e está associado a `response_model` no decorador.
- [ ] **Documentação amigável:** Todos os parâmetros e campos possuem `description` legível em português.
- [ ] **Paginação padronizada:** Usa `PaginationParams` (`page` e `per_page`), com limite máximo seguro (máximo 100 itens por página).
- [ ] **Ordenação padronizada:** Usa `SortParams` com whitelist estrita de campos (`sort_by`) e direção (`sort_order`).
- [ ] **Validação defensiva:** Parâmetros desconhecidos ou inválidos enviados na query string retornam código **HTTP 422**.
- [ ] **Registro no app principal:** O roteador foi adicionado com `v2_app.include_router(...)` em `src/simcc/v2/app.py`.
- [ ] **Visível no Swagger:** A rota aparece devidamente agrupada por tag ao acessar `/swagger`.
