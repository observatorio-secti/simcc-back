# Metodologia de Testes, Golden Dataset e Avaliação Semântica da MarIA

Este documento detalha a metodologia de testes da **MarIA**, com foco na elaboração do **Golden Dataset Assinado**, nos procedimentos de extração e reidratação (seeding), na execução dos testes em diferentes camadas e na avaliação quantitativa da qualidade de recuperação vetorial (*Retrieval Evaluation*).

---

## 🎯 Contexto e Desafios

Testar sistemas de **Busca Semântica Vetorial (RAG / Information Retrieval)** impõe desafios fundamentais que não existem em testes de CRUD tradicionais:

1. **Fidelidade Vetorial**: O comportamento de similaridade por cosseno (`pgvector`) depende de vetores reais calculados pelo modelo de *embedding* (`text-embedding-3-small`, 1536 dimensões). Mocks sintéticos com vetores aleatórios não reproduzem a distribuição de similaridade semântica do domínio acadêmico e científico baiano.
2. **Inviabilidade de Dumps Completos**: A base de dados real do SIMCC possui milhares de pesquisadores e dezenas de milhares de produções. Um dump completo ultrapassa centenas de megabytes, inviabilizando o versionamento via Git e tornando a execução de testes em pipelines de CI lenta e custosa.
3. **Integridade Relacional Estrita**: Tabelas especializadas de produção (`bibliographic_production_article`, `patent`, `software`, etc.) dependem de chaves estrangeiras para pesquisadores e instituições. Uma amostra isolada geraria erros de violação de *Foreign Key*.
4. **Reprodutibilidade Criptográfica**: Para garantir que avaliações de acurácia (Precision@k, Recall@k, MRR) sejam determinísticas ao longo de meses de desenvolvimento, a base de teste precisa ser **imutável e assinada**.

---

## 🏛️ O Golden Dataset Assinado

Para resolver esses desafios, foi concebida a estratégia do **Golden Dataset**: uma fatia mínima representativa, estatisticamente equilibrada, relacionalmente consistente e criptograficamente assinada.

```mermaid
graph LR
    subgraph "1. Extração Estratificada"
        DB[("🐘 Banco Local Real<br/>(localhost:5433)")] --> Extract["scripts/maria/<br/>extract_golden_sample.py"]
    end

    subgraph "2. Artefatos de Fixture"
        Extract --> JSON["sample_data.json<br/>(5.3 MB)"]
        Extract --> GZ["sample_data.json.gz<br/>(1.1 MB)"]
        Extract --> SHA["sample_data.sha256<br/>(Assinatura)"]
        Extract --> CAT["CATALOG.md<br/>(Inspeção Humana)"]
    end

    subgraph "3. Reidratação e Execução"
        JSON --> Seed["scripts/maria/<br/>seed_golden_sample.py"]
        Seed --> TestDB[("🐘 Testcontainers / CI<br/>PostgreSQL + pgvector")]
        TestDB --> Tests["pytest -m 'not ai_live'<br/>pytest -m ai_live"]
    end
```

### Arquivos Gerados (`tests/fixtures/golden_dataset/`)

| Arquivo | Tamanho | Descrição |
|---|---|---|
| [`sample_data.json`](file:///home/jaspion/Observatorio/Simcc/simcc-back/tests/fixtures/golden_dataset/sample_data.json) | ~5.3 MB | Snapshot completo das tabelas em formato JSON formatado, preservando IDs reais, metadados e vetores de 1536 dimensões. |
| [`sample_data.json.gz`](file:///home/jaspion/Observatorio/Simcc/simcc-back/tests/fixtures/golden_dataset/sample_data.json.gz) | ~1.1 MB | Versão compactada em GZIP (~80% menor), ideal para versionamento em repositórios remotos e clonagem rápida. |
| [`sample_data.sha256`](file:///home/jaspion/Observatorio/Simcc/simcc-back/tests/fixtures/golden_dataset/sample_data.sha256) | 65 B | Hash criptográfico SHA-256 do JSON de referência. Garante auditoria: qualquer adulteração de dado invalida a assinatura. |
| [`CATALOG.md`](file:///home/jaspion/Observatorio/Simcc/simcc-back/tests/fixtures/golden_dataset/CATALOG.md) | ~100 KB | Catálogo legível em Markdown contendo tabelas com Título, Ano, Autores, Instituição e prévia textual de cada documento. Permite ao time inspecionar os dados sem abrir arquivos JSON pesados. |

---

## 🔬 Como o Dataset foi Extraído

A extração é automatizada pelo script [`scripts/maria/extract_golden_sample.py`](file:///home/jaspion/Observatorio/Simcc/simcc-back/scripts/maria/extract_golden_sample.py):

### 1. Amostragem Estratificada
Para garantir representatividade de todas as modalidades de busca suportadas pelo SIMCC, foram extraídos:
* **30 Documentos de Pesquisadores** (`search_document_researcher`): abrangendo áreas como Computação, Medicina, Engenharia, Agronomia e Ciências Humanas.
* **30 Documentos por Tipo de Produção** (`search_document_production`):
  * **Artigos Periódicos** (`ARTICLE`): 30 registros
  * **Livros** (`BOOK`): 30 registros
  * **Capítulos de Livro** (`BOOK_CHAPTER`): 30 registros
  * **Relatórios Técnicos** (`REPORT`): 27 registros (todos os disponíveis na base)
  * **Softwares Registrados** (`SOFTWARE`): 4 registros (todos os disponíveis na base)
  * **Patentes Registradas** (`PATENT`): 2 registros (todos os disponíveis na base)
  * *Total: 123 produções com embeddings e 30 pesquisadores com embeddings.*

### 2. Resolução Recursiva de Dependências Estruturais
Para cada documento selecionado, o script mapeia recursivamente suas chaves estrangeiras:
1. **Instituições**: Identifica e extrai todos os registros de `institution` associados aos pesquisadores.
2. **Pesquisadores Pais**: Extrai os registros principais da tabela `researcher`.
3. **Produções Bibliográficas Base**: Extrai a tabela pai `bibliographic_production`.
4. **Periódicos e Revistas**: Extrai a tabela `periodical_magazine` vinculada aos artigos.
5. **Tabelas Específicas de Produção**: Extrai detalhes de cada subtipo (`bibliographic_production_article`, `bibliographic_production_book`, etc.).

### 3. Como Executar a Extração
Se no futuro for necessário atualizar ou expandir a amostra com novos dados:

```bash
# Executa a extração apontando para o banco de dados de referência
poetry run python scripts/maria/extract_golden_sample.py \
  --db-url "postgresql+asyncpg://postgres:postgres@localhost:5433/simcc" \
  --output-dir "tests/fixtures/golden_dataset"
```

---

## 🔄 Como Recuperar e Anexar a Base (Seeding)

Para usar o dataset em qualquer instância local, ambiente de homologação ou durante fixtures do Pytest, utiliza-se o script [`scripts/maria/seed_golden_sample.py`](file:///home/jaspion/Observatorio/Simcc/simcc-back/scripts/maria/seed_golden_sample.py).

### Propriedades da Reidratação
1. **Verificação de Assinatura**: O script calcula o hash SHA-256 do arquivo no momento da execução e valida contra o `sample_data.sha256`. Se o arquivo foi corrompido ou modificado, emite aviso imediato.
2. **Idempotência**: Todos os comandos SQL utilizam cláusulas `ON CONFLICT (id) DO NOTHING`. O script pode ser rodado múltiplas vezes sem erros de duplicidade ou violação de chaves.
3. **Casting Vetorial Adequado**: Os arrays de embeddings de ponto flutuante são inseridos no PostgreSQL com o casting nativo da extensão `(:embedding)::vector`.
4. **Tratamento de Tipos Nativos**: O `asyncpg` exige objetos `datetime` e `date` nativos do Python, que são convertidos automaticamente a partir das strings ISO 8601 do JSON.

### Execução via Linha de Comando

```bash
# Anexar ao banco padrão de desenvolvimento (localhost:5433)
poetry run python scripts/maria/seed_golden_sample.py

# Ou especificar uma URL personalizada (ex: container efêmero de testes)
poetry run python scripts/maria/seed_golden_sample.py \
  --db-url "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
```

### Uso Programático em Fixtures de Teste
O script expõe a função assíncrona `seed_golden_dataset`, que pode ser importada diretamente em conftests:

```python
from pathlib import Path
import pytest
from scripts.maria.seed_golden_sample import seed_golden_dataset

@pytest.fixture(scope="session")
async def golden_database(test_container_engine):
    """Popula o container de testes com a base assinada da MarIA."""
    db_url = str(test_container_engine.url)
    await seed_golden_dataset(db_url)
    yield test_container_engine
```

---

## 🧪 Como Executar a Suíte de Testes

O projeto adota uma matriz de testes em camadas, separando testes rápidos locais de testes que consomem chamadas reais de LLM:

### 1. Testes Rápidos e de Integração Offline (Padrão)
Executa 100% dos testes unitários, testes de contratos, testes de cache com Redis mockado/local e testes de regras de negócio, **sem gastar tokens de IA**:

```bash
# Via Taskipy
poetry run task test

# Ou diretamente via Pytest
poetry run pytest
```
> [!NOTE]
> Por padrão, a flag `-m 'not ai_live'` em `pyproject.toml` desmarca testes com consumo real de tokens da OpenAI. A suíte completa roda em menos de 7 segundos.

### 2. Testes Live Ponta-a-Ponta (com IA Real)
Para validar que os prompts, formatos estruturados de JSON e APIs da OpenAI continuam respondendo exatamente conforme os esquemas esperados:

```bash
# Exige a variável OPENAI_API_KEY no ambiente ou .env
export OPENAI_API_KEY="sk-..."
poetry run task test_live
```

### 3. Testes Específicos de Busca Vetorial e Limiar de Corte
Para testar especificamente o motor de recuperação vetorial (`AISearchService`) e a linha de corte cosseno:

```bash
# Teste de integração do serviço de busca vetorial
poetry run pytest tests/integration/services/test_ai_search_service.py -v

# Teste de comportamento do limiar de corte cosseno (cutoff)
poetry run pytest tests/unit/services/test_ai_search_cutoff.py -v
```

---

## 📊 Elaboração dos Casos de Avaliação Semântica (`EVALUATION_CASES`)

Com a base assinada fixada e o catálogo [`CATALOG.md`](file:///home/jaspion/Observatorio/Simcc/simcc-back/tests/fixtures/golden_dataset/CATALOG.md) disponível para consulta humana, a próxima etapa da esteira de qualidade consiste na definição do conjunto de avaliação do **Retrieval** (*Information Retrieval Evaluation*).

### Estrutura dos Casos de Teste

A equipe utiliza o catálogo para identificar o conjunto de *Ground Truth* (pesquisadores ou produções que obrigatoriamente devem ser recuperados para cada termo de busca):

```python
EVALUATION_CASES = [
    {
        "query": "pesquisadores especializados em inteligência artificial e aprendizado de máquina",
        "expected_intent": "researcher_search",
        "relevant_researcher_ids": {
            "4666f2c0-82a8-4ce6-90dc-a8fe37617b0d",
            "990f38b1-38cb-4034-9ca4-9b2f3479633e",
        },
    },
    {
        "query": "estudos sobre biodiesel, biocombustíveis e energias renováveis",
        "expected_intent": "production_search",
        "relevant_production_ids": {
            "f2e21245-0d3a-44ba-813c-829d63abfa64",
        },
    },
    {
        "query": "pesquisas em saúde pública e epidemiologia da dengue na Bahia",
        "expected_intent": "researcher_search",
        "relevant_researcher_ids": {
            "7b69234b-b8f9-4d22-83fc-db8c31cb1f3a",
        },
    },
]
```

### Métricas de Qualidade Calculadas

Contra o Golden Dataset, cada alteração no limiar de corte (`AI_COSINE_DISTANCE_THRESHOLD`) ou na engenharia de prompt do `QueryPlanner` é avaliada quantitativamente pelas métricas:

1. **Precision@k (Precisão no Top-K)**:  
   $$\text{Precision@k} = \frac{|\text{Documentos Relevantes no Top-K}|}{K}$$  
   *Mede quanto do que a MarIA trouxe é útil, evitando que documentos irrelevantes passem pelo filtro.*

2. **Recall@k (Revocação no Top-K)**:  
   $$\text{Recall@k} = \frac{|\text{Documentos Relevantes no Top-K}|}{|\text{Total de Relevantes Conhecidos}|}$$  
   *Mede a capacidade da MarIA de não deixar pesquisadores ou artigos fundamentais de fora da resposta.*

3. **MRR (Mean Reciprocal Rank)**:  
   $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$  
   *Mede a posição do primeiro documento relevante retornado. Se o melhor especialista for sempre o primeiro item (rank 1), o MRR é 1.0.*

> [!TIP]
> **Vantagem Competitiva**: Com o Golden Dataset assinado, o SIMCC possui uma métrica de qualidade quantitativa contra regressões silenciosas — antes de colocar qualquer mudança de prompt ou modelo em produção, a equipe pode comprovar se a acurácia de busca subiu ou desceu percentualmente.

---

## 📁 Inventário de Scripts da MarIA

Todos os scripts que compõem este ecossistema estão centralizados no diretório [`scripts/maria/`](file:///home/jaspion/Observatorio/Simcc/simcc-back/scripts/maria):

```
scripts/maria/
├── __init__.py                # Módulo Python com exportações utilitárias
├── README.md                  # Documentação rápida de comandos de terminal
├── ingest_researchers.py      # Popula e calcula embeddings de pesquisadores
├── ingest_productions.py      # Popula e calcula embeddings de produções científicas
├── extract_golden_sample.py   # Extrai amostra equilibrada e gera assinatura SHA-256
└── seed_golden_sample.py      # Popula a amostra assinada em qualquer banco PostgreSQL
```
