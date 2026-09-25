# 1. Criação de Rotinas e Serviços

No SIMCC V2, uma **rotina ou serviço** representa uma operação de negócio do sistema. Pode ser uma busca orquestrada, uma agregação de facets, ou uma rotina periódica de sincronização (como o refresh das visões materializadas).

---

## Onde as Rotinas Vivem?

As regras de negócio ficam centralizadas na camada de **Serviços** (`src/simcc/v2/services/`).

```
Routers (HTTP)  ───►  Services (Regras e Orquestração)  ───►  Repositories (Banco de Dados)
```

Essa separação garante que o serviço possa ser chamado tanto por um endpoint HTTP quanto por um comando CLI, uma fila assíncrona ou uma rotina agendada (cron), sem qualquer dependência de requisições web.

---

## Boas Práticas na Criação de Serviços

1. **Nunca faça consultas em loops (Evite o problema N+1):** Se você precisa de dados de 20 pesquisadores, nunca execute 20 consultas individuais. Faça uma única consulta em lote usando `WHERE id = ANY(:ids)` ou `IN (...)`.
2. **Tipagem Estrita:** Funções de serviço devem receber e retornar modelos Pydantic ou dataclasses. Evite manipular dicionários genéricos (`dict[str, Any]`), pois eles facilitam erros de digitação e dificultam a manutenção.
3. **Isolamento de HTTP:** O serviço não deve receber objetos do FastAPI como `Request` ou `Response`. Ele deve receber apenas dados limpos (objetos de filtro, paginação e sessão de banco).
4. **Respeito ao Orçamento de Consultas:** Todo serviço deve saber com precisão quantas queries dispara ao banco de dados.

---

## Exemplo: Rotinas em Segundo Plano (Refresh de MVs)

Um exemplo prático de rotina de manutenção na V2 é o serviço de sincronização [`mv_refresh_service.py`](file:///home/jaspion/Observatorio/Simcc/simcc-back/src/simcc/v2/services/mv_refresh_service.py):

* Executa a atualização concorrente das visões materializadas na ordem correta de dependência.
* Registra o horário da conclusão na tabela de controle e atualiza o estado em memória da aplicação.
* Garante que qualquer busca subsequente conheça o horário dos dados (`data_as_of`) sem custos de query adicionais.

---

## Checklist para Criação de Rotinas e Serviços

Utilize este checklist sempre que criar ou alterar um serviço na V2:

- [ ] **Localização correta:** O arquivo está dentro de `src/simcc/v2/services/` (ex: `meu_recurso_service.py`).
- [ ] **Independência de HTTP:** A função não recebe `Request` nem depende de detalhes da camada web.
- [ ] **Tipagem completa:** Todos os argumentos e o retorno da função possuem anotações de tipo (`-> TipoRetorno:`).
- [ ] **Sem consultas em loops:** Todas as buscas ao banco de dados são feitas em lote (batching).
- [ ] **Orçamento previsível:** O número de consultas ao banco é constante ou estritamente proporcional aos parâmetros opcionais (opt-in).
- [ ] **Tratamento de exceções:** Validações de negócio disparam erros apropriados (ex.: `HTTPException(422, detail=...)` para parâmetros inconsistentes).
- [ ] **Sem efeitos colaterais ocultos:** O serviço não altera estados globais sem documentação explícita.
