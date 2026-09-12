# SIMCC - Backend (API & Extrator)

Backend do **SIMCC** (Sistema de Informação e Mapeamento da Competência Científica), uma plataforma desenvolvida e mantida sob o guarda-chuva do **Observatório SECTI** (Secretaria de Ciência, Tecnologia e Inovação).

---

## 📌 Sobre o Projeto

O **SIMCC** é uma plataforma analítica e estratégica voltada para o mapeamento, integração e inteligência sobre a produção científica, tecnológica, patentes, projetos e redes de colaboração de pesquisadores e instituições. 

Integrado ao ecossistema do **Observatório SECTI**, o SIMCC consolida dados de múltiplas fontes (como a Plataforma Lattes/CNPq, OpenAlex, bases institucionais e de fomento), provendo:
- **Busca Semântica e Filtros Avançados**: Consultas combinadas por termos, áreas do conhecimento, instituições, programas de pós-graduação e cidades.
- **Métricas e Indicadores Analíticos**: Produção bibliográfica, propriedade intelectual, orientações, projetos de pesquisa e evolução temporal.
- **Camada de Inteligência Artificial (Maria / LLM)**: Assistente integrada para processamento de linguagem natural, sumarizações e extração de insights acadêmicos.
- **Rotinas de Ingestão e Sincronização**: Pipeline automatizado de extração de dados Lattes via XML (Apache Hop) e sincronização contínua com bases administrativas.

---

## 🛠️ Tecnologias Principais

- **Linguagem & Runtime**: Python 3.13+
- **Framework Web**: [FastAPI](https://fastapi.tiangolo.com/) (Pydantic v2 + Pydantic Settings)
- **Banco de Dados & ORM**: PostgreSQL 17 + [pgvector](https://github.com/pgvector/pgvector), SQLAlchemy 2.0 (Async com `asyncpg` e `psycopg3`), [Alembic](https://alembic.sqlalchemy.org/)
- **Qualidade & Estilo**: [Ruff](https://docs.astral.sh/ruff/) (Linter & Formatter)
- **Testes & Mocks**: [Pytest](https://docs.pytest.org/), Testcontainers (PostgreSQL), FactoryBoy, Respx
- **Gerenciador de Dependências**: [Poetry](https://python-poetry.org/) e [Taskipy](https://github.com/illBeRoy/taskipy)

---

## ⚙️ Configuração de Variáveis de Ambiente (`.env`)

A aplicação utiliza o `pydantic-settings` através do arquivo [`src/simcc/core/settings.py`](src/simcc/core/settings.py). Crie um arquivo `.env` na raiz do projeto:

```bash
cp .env.example .env  # ou crie o arquivo .env conforme tabela abaixo
```

### Parâmetros Suportados

| Variável | Tipo | Padrão | Obrigatório | Descrição |
| :--- | :--- | :--- | :---: | :--- |
| `DATABASE_URL` | String | - | **Sim** | URL de conexão assíncrona com o PostgreSQL principal (ex: `postgresql+asyncpg://postgres:postgres@localhost:5432/simcc`). |
| `ADMIN_DATABASE_URL` | String | - | **Sim** | URL de conexão com o banco administrativo do SIMCC (ex: `postgresql+asyncpg://postgres:postgres@localhost:5432/simcc_admin`). |
| `COMPOSE_PROJECT_NAME` | String | `simcc` | Não | Nome do projeto/banco utilizado no `compose.yaml`. |
| `DB_PORT` | Inteiro | `5432` | Não | Porta mapeada para o banco PostgreSQL local no Compose. |
| `API_PORT` | Inteiro | `8000` | Não | Porta mapeada para a API no Compose. |
| `URL` | String | `http://localhost:0000/` | Não | URL base pública do serviço da API. |
| `ADMIN_URL` | String | `http://localhost:0000/` | Não | URL base do serviço administrativo. |
| `OPENAI_API_KEY` | String | `None` | Não | Chave de API da OpenAI para as rotinas e provedores de IA. |
| `INTERNAL_API_KEY` | String | `None` | Não | Chave de autenticação interna para rotas protegidas/administrativas. |
| `LOG_STREAM_TOKEN` | String | `None` | Não | Token de autorização para streaming de logs via websocket/endpoint. |
| `CORS_ALLOW_ORIGINS` | List/CSV | `*` | Não | Origens permitidas para requisições CORS (aceita lista JSON ou valores separados por vírgula). |
| `CORS_ALLOW_METHODS` | List/CSV | `*` | Não | Métodos HTTP permitidos no CORS. |
| `CORS_ALLOW_HEADERS` | List/CSV | `*` | Não | Headers HTTP permitidos no CORS. |
| `CORS_ALLOW_CREDENTIALS` | Bool | `True` | Não | Permite ou restringe envio de credenciais/cookies nas requisições. |
| `FIREBASE_COLLECTION` | String | `termos_busca` | Não | Nome da coleção utilizada no Firestore/Firebase. |
| `FIREBASE_CERT_PATH` | String | `cert.json` | Não | Caminho do arquivo de credenciais do Firebase Admin SDK. |
| `XML_PATH` | String | `storage/xml` | Não | Diretório base para armazenamento dos XMLs dos currículos Lattes. |
| `CURRENT_XML_PATH` | String | `storage/xml/current` | Não | Diretório com os XMLs da extração vigente. |
| `ZIP_XML_PATH` | String | `storage/xml/current` | Não | Diretório para arquivamento compactado dos XMLs. |
| `ALTERNATIVE_CNPQ_SERVICE` | Bool | `False` | Não | Flag para acionar o endpoint alternativo do web service CNPq. |
| `HOP_IMAGE` | String | `gleidsoncosta/simcc-extrator:latest` | Não | Imagem Docker do extrator Apache Hop. |
| `HOP_XML_VOLUME` | String | `simcc_xml` | Não | Nome do volume Docker compartilhado com os XMLs do extrator. |
| `HOP_NETWORK` | String | `simcc-back_default` | Não | Rede Docker na qual o contêiner do Apache Hop é executado. |
| `APPLICATION` | String | `simcc` | Não | Identificador da aplicação para estruturação de logs. |
| `ENVIRONMENT` | String | `development` | Não | Ambiente de execução (`development`, `staging`, `production`). |
| `LOG_LEVEL` | String | `INFO` | Não | Nível de verbosidade do logger (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_DIR` | String | `logs` | Não | Diretório para persistência de logs rotativos estruturados. |
| `LOG_RETENTION_DAYS` | Inteiro | `7` | Não | Período em dias para limpeza e expiração automática dos arquivos de log. |

---

## 🚀 Como Rodar a Aplicação

### 1. Via Docker Compose (Recomendado)

Sobe todos os serviços necessários (PostgreSQL com `pgvector`, API FastAPI e Extrator Hop):

```bash
docker compose up --build -d
```

Verifique o status dos serviços e acompanhe os logs:
```bash
docker compose ps
docker compose logs -f api
```

A API estará disponível em `http://localhost:8000`.

---

### 2. Ambiente de Desenvolvimento Local (Poetry)

#### Pré-requisitos:
- Python 3.13+
- Poetry (`pipx install poetry` ou via `curl`)
- Instância do PostgreSQL com as extensões `unaccent` e `vector` ativas.

#### Instalação das dependências:
```bash
poetry install
```

#### Executar migrações do banco:
```bash
poetry run alembic upgrade head
```

#### Iniciar o servidor de desenvolvimento:
Utilizando o Taskipy:
```bash
poetry run task run
```
Ou diretamente com a CLI do FastAPI:
```bash
poetry run fastapi dev src/simcc --reload-dir "src/simcc"
```

#### Documentação Interativa:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🗄️ Fluxo de Migrações com Alembic

O banco de dados é versionado através do [Alembic](https://alembic.sqlalchemy.org/). Para manter a consistência e integridade do schema, siga o fluxo abaixo:

### Passo a Passo para Atualizações de Modelos

1. **Alterar ou Criar os Modelos SQLAlchemy**:
   - Edite os modelos existentes ou crie novos dentro de [`src/simcc/core/db/models/`](src/simcc/core/db/models/).
   - Certifique-se de que os novos modelos estejam expostos em [`src/simcc/core/db/model.py`](src/simcc/core/db/model.py) para que o `table_registry` registre os metadados.

2. **Gerar a Migração Automática**:
   Execute o comando `revision --autogenerate` descrevendo a mudança:
   ```bash
   poetry run alembic revision --autogenerate -m "adiciona_campo_x_na_tabela_y"
   ```

3. **Revisar e Ajustar o Arquivo Gerado (Essencial)**:
   - Abra o script recém-criado em `migrations/versions/<hash>_adiciona_campo_x_na_tabela_y.py`.
   - **Atenção**: O `autogenerate` do Alembic é uma ferramenta auxiliar e pode não detectar alterações complexas (como schemas específicos, triggers, tipos ENUM, extensões ou índices parciais).
   - Valide se as funções `upgrade()` e `downgrade()` estão corretas, seguras e reversíveis.

4. **Aplicar a Migração no Banco**:
   ```bash
   poetry run alembic upgrade head
   ```

### Comandos Úteis do Alembic:
- Reverter a última migração:
  ```bash
  poetry run alembic downgrade -1
  ```
- Exibir histórico de migrações:
  ```bash
  poetry run alembic history --verbose
  ```
- Exibir versão atual aplicada no banco:
  ```bash
  poetry run alembic current
  ```

---

## 🎨 Boas Práticas e Padrões de Código (Ruff)

O projeto adota o **[Ruff](https://docs.astral.sh/ruff/)** como linter e formatador oficial de código.

### Configurações Definidas no Projeto (`pyproject.toml`):
- **Tamanho de linha (`line-length`)**: Máximo de **79 caracteres**.
- **Estilo de aspas (`quote-style`)**: Aspas simples (`'single'`).
- **Regras ativas no Lint**:
  - `I` (isort - ordenação de imports)
  - `F` (Pyflakes - erros de sintaxe e variáveis não utilizadas)
  - `E` / `W` (pycodestyle - formatação e estilo PEP 8)
  - `PL` (Pylint - convenções e boas práticas de design)
  - `PT` (flake8-pytest-style - convenções para testes pytest)
- **Pastas ignoradas**: `migrations/` possui regras flexibilizadas para preservar os templates gerados pelo Alembic.

### Comandos do Ruff:

- **Verificar problemas de linting**:
  ```bash
  poetry run ruff check .
  ```
- **Aplicar correções automáticas**:
  ```bash
  poetry run ruff check . --fix
  ```
- **Formatar todo o código-fonte**:
  ```bash
  poetry run ruff format .
  ```

---

## 🧪 Estratégia e Execução de Testes

A suíte de testes utiliza **Pytest**, **Testcontainers** e **FactoryBoy**, organizada em duas categorias:

1. **Tier A (Unidade / Query Objects)**: Testes rápidos e isolados (sem overhead de banco) que validam a lógica de filtros e a construção de cláusulas SQL dinâmicas.
2. **Tier B (Integração Semântica)**: Testes que sobem contêineres reais do PostgreSQL via `testcontainers` para validar extensões (`unaccent`, `pgvector`), integridade relacional e rotas FastAPI.

### Comandos para Testes:

- **Executar todos os testes com cobertura** (via Taskipy):
  ```bash
  poetry run task test
  ```
- **Gerar relatório HTML de cobertura**:
  ```bash
  poetry run task cov
  ```
- **Executar apenas testes unitários**:
  ```bash
  poetry run pytest -m unit
  ```
- **Executar testes de integração**:
  ```bash
  poetry run pytest -m integration
  ```
- *(Opcional)* Testes com chamadas reais à OpenAI (consomem créditos):
  ```bash
  poetry run pytest -m ai_live
  ```

---
### Comandos de Scripts

#### Importação de docentes por instituição
**Opções da CLI:**

| Opção | Obrigatória | Descrição |
| --- | --- | --- |
| `--file` ou `-f` | Sim | Caminho do arquivo CSV ou `.xlsx`. Use aspas quando houver espaços. |
| `--inst` | Sim | Sigla cadastrada no banco e em `INSTITUTION_FORMATS`, como `EBMSP` ou `UFOB`. |
| `--dry-run` | Não | Consulta o banco e o ViaCEP e gera o relatório sem gravar alterações no banco. |

**Simular a importação:** substitua os caminhos dos exemplos pelos arquivos recebidos.

```powershell
poetry run python scripts/ingest/ingest_researcher_affiliations.py --inst EBMSP --file "storage/docentes_ebmsp.csv" 
poetry run python scripts/ingest/ingest_researcher_affiliations.py --inst UFOB --file "storage/docentes_ufob.xlsx" 
```

**Gravar os dados:** execute o mesmo comando sem `--dry-run`.

```powershell
poetry run python scripts/ingest/ingest_researcher_affiliations.py --inst EBMSP --file "storage/docentes_ebmsp.csv"
```

## 🏛️ Estrutura Arquitetural

O projeto adota uma arquitetura em camadas visando desacoplamento e testabilidade:

```text
src/simcc/
├── ai/              # Provedores de IA, schemas, prompts e query planner
├── core/            # Configurações globais, banco de dados, segurança e logging estruturado
│   └── db/          # Conexão de banco e modelos declarativos SQLAlchemy
├── queries/         # Padrão Query Object para construção de queries SQL dinâmicas complexas
├── repositories/    # Camada de acesso a dados e orquestração de queries
├── routers/         # Controladores da API FastAPI (endpoints REST)
├── schemas/         # Modelos Pydantic (DTOs) para entrada e saída de dados
├── services/        # Regras de negócio e casos de uso da aplicação
└── static/          # Arquivos estáticos e logs
```

Mais detalhes sobre a arquitetura e diretrizes de desenvolvimento podem ser consultados no diretório [`docs/`](docs/).
