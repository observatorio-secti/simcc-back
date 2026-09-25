# 3. Criação de Testes

No SIMCC V2, os testes são projetados para serem **simples, diretos, rápidos e totalmente isolados**. Eles garantem que novas implementações não quebrem funcionalidades existentes nem introduzam regressões.

---

## Como o Ambiente de Testes Funciona

* **PostgreSQL e Redis Reais via Testcontainers:** Os testes da V2 não usam bancos em memória simplificados (como SQLite) nem mocks de cache, pois precisamos testar recursos reais: índices GIN, busca textual unaccent, Visões Materializadas e o [cache de buscas](../conceitos/cache.md).
* **Fábricas de Dados (Factories):** Você não precisa criar registros manualmente com SQL complexo. Utilizamos factories prontas que criam entidades com dados consistentes e realistas:
  * `researcher_factory(...)` (atualiza as MVs e invalida o cache ao final)
  * `institution_factory(...)`
  * `graduate_program_factory(...)`
  * `researcher_institution_factory(...)` e `city_factory(...)`
* **Localização dos Testes:** Todos os testes unitários da V2 residem na pasta `tests/v2/unit/`.

### Infraestrutura: containers, fixtures e `client`

Banco e cache seguem a mesma estrutura: um container por execução da suíte, um recurso isolado por teste e a injeção no app via `dependency_overrides`.

| | Banco de dados | Cache |
|---|---|---|
| **Container (escopo de sessão)** | `engine` | `redis_container` |
| **Recurso por teste** | `session` (transação desfeita ao final) | `cache` (Redis limpo antes e depois) |
| **Injetado no app como** | `get_async_session` | `get_search_cache` |

O fixture `client` já injeta os dois: todo teste de endpoint roda com banco **e cache ligados**, como em produção.

!!! warning "Mudou os dados? Use `refresh_mvs`"
    Em produção, as MVs só mudam pela rotina de refresh, que também invalida o cache. Nos testes é igual: depois de inserir dados direto pela `session`, chame o fixture `refresh_mvs()` em vez de `refresh_search_materialized_views`. Sem a invalidação, a próxima requisição pode receber uma resposta antiga do cache.

    ```python
    async def test_exemplo(client, session, researcher_factory, refresh_mvs):
        researcher = await researcher_factory()
        session.add(ResearcherProduction(researcher_id=researcher.id, articles=3))
        await session.commit()
        await refresh_mvs()

        response = client.get('/v2/researcher')
    ```

Para inspecionar o Redis diretamente num teste, use o fixture `redis_url` com um cliente síncrono (`redis.Redis.from_url(redis_url)`).

---

## O que Todo Endpoint ou Recurso Deve Testar

Ao criar ou modificar um recurso, certifique-se de cobrir quatro cenários essenciais:

```
┌────────────────────────────────────────────────────────┐
│  1. Caminho Feliz (Status 200 e estrutura correta)     │
│  2. Validações e Erros (Status 422 em dados inválidos) │
│  3. Paginação e Limites (Sem itens perdidos/repetidos) │
│  4. Orçamento de Consultas (Auditado via cursor)       │
└────────────────────────────────────────────────────────┘
```

### 1. Caminho Feliz (Status 200)
Garante que, com entradas corretas, a API retorna código 200 e o payload possui todos os campos esperados (dados, paginação, metadados).

### 2. Validações Defensivas (Status 422)
Garante que o FastAPI barra dados incorretos antes de executar consultas caras no banco:
* Intervalo de datas invertido (`year_start > year_end`).
* Valores fora dos limites (`per_page=0` ou `per_page=101`).
* Parâmetros desconhecidos na query string (ex.: `?parametro_inexistente=123`).
* Ordenação por relevância sem fornecer o termo de busca `q`.

### 3. Paginação e Ordenação
Garante que percorrer a página 1, 2 e 3 não repita registros nem perca itens, mesmo quando vários registros possuem o mesmo nome ou nota.

### 4. Orçamento de Consultas (Query Budget)
Para rotas complexas, utilize o evento do SQLAlchemy para auditar o número exato de comandos `SELECT` executados, garantindo que ninguém introduziu queries N+1 por engano.

---

## Como Executar os Testes

Execute a suíte de testes da V2 com um único comando pelo terminal:

```bash
# Rodar todos os testes unitários da V2
poetry run pytest tests/v2/unit

# Rodar apenas um arquivo de testes específico
poetry run pytest tests/v2/unit/test_search_features.py

# Rodar verificações de estilo e formatação
poetry run ruff check src/simcc/v2 tests/v2
poetry run ruff format --check src/simcc/v2 tests/v2
```

---

## Checklist para Criação de Testes

Use este checklist para validar sua suíte de testes antes de submeter sua contribuição:

- [ ] **Arquivo criado no local correto:** `tests/v2/unit/test_<nome_do_recurso>.py`.
- [ ] **Marcador assíncrono:** Todas as funções de teste usam o decorador `@pytest.mark.asyncio`.
- [ ] **Isolamento de dados:** O teste cria apenas os registros necessários usando as factories disponibilizadas.
- [ ] **Cenário de sucesso testado:** Verifica status HTTP 200 e campos da resposta.
- [ ] **Cenários de erro testados:** Verifica status HTTP 422 para valores inválidos e parâmetros desconhecidos.
- [ ] **Paginação testada:** Verifica se o comportamento respeita `page` e `per_page`.
- [ ] **Suíte 100% verde:** O comando `poetry run pytest tests/v2/unit` passa sem falhas ou warnings críticos.
- [ ] **Padrão de código:** Passou com sucesso por `ruff check` e `ruff format`.
