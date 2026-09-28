# Guia de Contribuição - V2

Seja bem-vindo ao desenvolvimento da **V2** do SIMCC! Este guia foi feito para que desenvolvedores de qualquer nível consigam entender a organização do código e contribuir com segurança.

---

## Estrutura de Pastas da V2

Todo o código da V2 está isolado dentro de `src/simcc/v2/`. A separação de responsabilidades segue a arquitetura em camadas:

```
src/simcc/v2/
├── app.py                  # Ponto central de montagem das rotas da V2
├── routers/                # Controladores HTTP (recebem parâmetros e chamam serviços)
├── services/               # Regras de negócio, validações e orquestração
├── repositories/           # Acesso ao banco de dados e consultas SQL / SQLAlchemy
└── schemas/                # Modelos Pydantic (validação de entrada e saída)
```

### Onde colocar cada coisa?

* **`schemas/`:** Se você precisa definir formatos de dados (ex: parâmetros de busca, objetos retornados pela API), crie ou edite arquivos aqui.
* **`repositories/`:** Se você precisa fazer uma consulta ao PostgreSQL ou montar condições `WHERE`, a lógica fica aqui.
* **`services/`:** Se você precisa combinar dados, calcular tempo de execução, validar regras de negócio ou aplicar políticas, implemente aqui.
* **`routers/`:** Se você precisa expor uma URL para o mundo externo via FastAPI, registre a função aqui.

---

## Os Três Passos da Contribuição

Para facilitar o aprendizado, dividimos o processo de contribuição em três etapas práticas, cada uma com seu próprio checklist:

1. [**Criação de Rotinas e Serviços**](rotinas.md): Como estruturar lógica de negócio e tarefas sem sobrecarregar o banco de dados.
2. [**Criação de Endpoints**](endpoints.md): Como criar e registrar novas rotas seguindo os padrões de parâmetros e segurança da V2.
3. [**Criação de Testes**](testes.md): Como garantir que seu código funciona e não quebra outros recursos do sistema.
