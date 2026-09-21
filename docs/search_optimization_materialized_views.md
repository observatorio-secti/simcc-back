# Arquitetura de Busca Textual Granular (FTS) em Duas Camadas

## 1. Contexto e Objetivos

O SIMCC agrega competências científicas e tecnológicas de múltiplas fontes heterogêneas (Currículo Lattes, OpenAlex, bases de patentes e registros de software). 

Uma abordagem puramente agregada (onde todas as fontes são fundidas em um único documento por pesquisador em uma DDL monolítica) apresenta dois desafios estruturais:
1. **Acoplamento de Manutenção:** A inclusão de novas fontes de dados (ex.: projetos de pesquisa, orientações) exige alterar uma consulta monolítica centralizada e reprocessar todos os índices.
2. **Perda de Rastreabilidade (Granularidade):** Ao consolidar todas as produções em um único vetor textual por pesquisador, perde-se a capacidade de apontar **onde** a competência foi encontrada (ex.: qual artigo, patente ou livro gerou o casamento com o termo buscado).

### Objetivo Arquitetural
Desenvolver uma arquitetura de busca em **duas camadas desacopladas**:
- **Alta performance em paginação e ranking:** Consulta rápida em nível de pesquisador (1 linha por pesquisador).
- **Rastreabilidade e Snippets (`matched_in`):** Detalhamento sob demanda dos documentos específicos que atenderam à busca na página atual.

---

## 2. Visão Conceitual das Camadas

A arquitetura organiza os dados em duas camadas com granularidades e responsabilidades distintas:

| Dimensão | Camada 1: Granularidade por Documento | Camada 2: Granularidade por Pesquisador |
| :--- | :--- | :--- |
| **Escopo** | 1 registro por produção (artigo, livro, patente, software). | 1 registro consolidado por pesquisador ativo. |
| **Materialização** | MVs independentes por fonte (`mv_search_*`). | MV agregada via união das fontes (`mv_researcher_search`). |
| **Objetivo na Busca** | Fornecer snippets (`ts_headline`) e documentos casados (`matched_in`). | Ranqueamento ponderado global (`ts_rank_cd`), filtros estruturais e paginação. |
| **Acoplamento** | Zero acoplamento entre fontes distintas. | Acoplamento leve via união polimórfica (`UNION ALL`). |
| **Custo de Atualização** | Isolado: rotina de patentes atualiza apenas a visão de patentes. | Reavalia a agregação apenas dos vetores já pré-computados. |

---

## 3. Modelo de Dados e Enums Conceituais

### A. Tipos de Fonte de Informação (`SourceType`)
Classificação da origem do documento associado à competência encontrada:

| Valor Enum | Descrição | Origem no Banco |
| :--- | :--- | :--- |
| `PROFILE` | Dados do próprio perfil do pesquisador | `researcher` (nome, resumo Lattes) |
| `ARTICLE` | Artigos publicados em periódicos | `bibliographic_production` + `openalex_article` |
| `BOOK` | Livros autorais ou organizados | `bibliographic_production` |
| `BOOK_CHAPTER` | Capítulos de livros publicados | `bibliographic_production` |
| `PATENT` | Patentes registradas ou concedidas | `patent` |
| `SOFTWARE` | Softwares e programas de computador | `software` |

---

### B. Campos de Correspondência (`MatchField`) e Tipos de Match (`MatchType`)

| Classificação | Valores | Finalidade |
| :--- | :--- | :--- |
| **Campo Casado (`field`)** | `name`, `abstract`, `title`, `keywords` | Identifica a seção exata do documento que motivou o resultado. |
| **Tipo de Busca (`match_type`)** | `fts`, `fuzzy` | Distingue se a correspondência foi semântico-textual (stemming via `tsvector`) ou fonético-ortográfica (aproximação via `pg_trgm`). |

---

### C. Contrato Uniforme das Visões de Fonte (Camada 1)

Todas as visões da Camada 1 implementam o mesmo contrato colunar polimórfico:

| Coluna | Tipo | Finalidade Conceitual |
| :--- | :--- | :--- |
| `researcher_id` | `UUID` | Chave estrangeira de junção e particionamento lógico. |
| `source_id` | `UUID` | Identificador único do documento original (chave primária da MV). |
| `source_type` | `Text` | Identificador da fonte (`ARTICLE`, `PATENT`, etc.). |
| `title` | `Text` | Título legível da produção para exibição no frontend. |
| `year_` | `Integer` | Ano de referência (extraído da produção ou patente). |
| `abstract` | `Text` | Texto descritivo para geração de fragmentos de destaque (`snippet`). |
| `search_vector` | `tsvector` | Vetor de busca pré-ponderado com normalização gráfica. |

---

## 4. Política de Ponderação e Calibragem de Relevância

Para garantir relevância justa entre termos curtos (nomes de pessoas) e conteúdos densos (resumos científicos), o ranqueamento é calibrado em dois níveis:

1. **Atribuição Estrutural de Letras (`setweight` nas MVs):** Categoriza semanticamente a importância de cada campo no vetor textual.
2. **Ponderação Numérica em Tempo de Consulta (`ts_rank_cd` no Repositório):** Converte as letras em pontuações numéricas relativas na ordenação final.

### Matriz de Pesos e Atribuição de Pontos

| Atributo / Campo | Letra PostgreSQL | Peso Numérico Atual | Mapeamento no Código | Justificativa Arquitetural |
| :--- | :---: | :---: | :--- | :--- |
| **Nome do Pesquisador** | **`A`** | **`1.0`** | `mv_researcher_search` | **Identidade e autoria**: busca direta pelo pesquisador sempre domina o topo. |
| **Títulos de Produções** <br>(Artigos, Livros, Patentes, Softwares) | **`B`** | **`0.4`** | `mv_search_*` (Camada 1) | **Alta relevância**: síntese primária da temática do trabalho. |
| **Palavras-chave e Resumo Lattes** | **`C`** | **`0.2`** | `mv_search_articles` / `mv_researcher_search` | **Média relevância**: termos de indexação e contexto de atuação. |
| **Resumo Longo de Artigos** (OpenAlex) | **`D`** | **`0.1`** | `mv_search_articles` | **Relevância de suporte**: menções e aprofundamento textual. |

---

### Guia de Ajuste e Calibragem no Código

#### 1. Calibragem Numérica Imediata (Sem reprocessar o banco)
Para ajustar a sensibilidade ou dar mais/menos pontos a cada tipo de ocorrência, modifique a função de ordenação no repositório:

📁 `src/simcc/v2/repositories/researcher_repo.py`

```python
# O array do PostgreSQL segue a ordem estrita {D, C, B, A} e os valores DEVEM estar no intervalo [0.0, 1.0]:
"ts_rank_cd('{0.1, 0.2, 0.4, 1.0}', search_vector, query) AS relevance_score"
```

> **Restrição do PostgreSQL:** Os valores do array de pesos devem ser do tipo `float4` situados estritamente entre `0.0` e `1.0`. Valores superiores a `1.0` disparam o erro de banco `InvalidParameterValue: weight out of range`.

* **Priorizar mais os títulos em relação aos resumos:** eleve o peso `B` relativamente a `C` e `D` (ex.: `{0.05, 0.1, 0.6, 1.0}`).
* **Controlar viés de documentos muito longos:** adicione a flag de normalização `32` ao `ts_rank_cd` (calcula o rank ponderado dividindo pela extensão do documento):
  ```sql
  ts_rank_cd('{0.1, 0.2, 0.4, 1.0}', search_vector, query, 32)
  ```

#### 2. Reclassificação Estrutural de Categorias
Para alterar quais campos pertencem a cada letra (`A`, `B`, `C` ou `D`):

📁 `migrations/versions/e7796887be76_create_search_materialized_views.py`

* As visões da Camada 1 definem o peso na origem (`setweight(to_tsvector(...), 'B')`).
* A Camada 2 consolida e preserva os pesos originais via concatenação vetorial (`||`), sem recalculá-los.
* *Nota:* Alterações nas letras de `setweight` exigem executar `REFRESH MATERIALIZED VIEW` para que os índices reflitam os novos pesos.

---

## 5. Estratégia de Execução em Duas Fases (`/v2/researcher`)

Para assegurar tempos de resposta previsíveis sem transferência massiva de dados pela rede, o fluxo de consulta divide-se em duas etapas:

```
[Requisição HTTP]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│  Fase 1: Ranking e Paginação (Camada 2)                │
│  - Avalia termo contra mv_researcher_search            │
│  - Aplica filtros de instituição e pós-graduação       │
│  - Ordena por ts_rank_cd e extrai LIMIT/OFFSET         │
└────────────────────────────────────────────────────────┘
       │
       │ Retorna IDs dos pesquisadores da página (ex: 20 registros)
       ▼
┌────────────────────────────────────────────────────────┐
│  Fase 2: Resolução Granular de Evidências (Camada 1)   │
│  - Consulta indexada apenas para os 20 IDs da página   │
│  - Recupera os 2-3 documentos mais relevantes por autor│
│  - Gera snippets destacados (<mark>) via ts_headline   │
└────────────────────────────────────────────────────────┘
       │
       ▼
[Montagem do Envelope Padronizado com matched_in]
```

---

## 6. Rastreabilidade de Metadados e Ciclo de Vida

### Sincronização e Atualização Concorrente

A hierarquia de dependência entre as visões exige uma ordem estrita de execução:

1. **Camada 1 (Fontes de Produção):** Devem ser atualizadas primeiro para refletir os novos registros ou alterações nos dados brutos.
2. **Camada 2 (Pesquisador Consolidado):** Atualizada em seguida, pois consome os vetores já ponderados e estruturados da Camada 1.

#### Modos de Atualização

| Modo | Escopo | Quando Utilizar |
| :--- | :--- | :--- |
| **Atualização Total (*Full Refresh*)** | Camada 1 (todas) ➔ Camada 2 | Fechamento de ciclo de ingestão geral (ex.: execução completa de ETL / `post_hop.sh`). |
| **Atualização Parcial (*Targeted Refresh*)** | Camada 1 (fonte alterada) ➔ Camada 2 | Atualização diária ou periódica de uma única base (ex.: nova carga de artigos do OpenAlex ou patentes do INPI). |

#### Atualização Não-Bloqueante (`CONCURRENTLY`)

Para garantir que a API pública `/v2/researcher` e os usuários continuem realizando consultas sem tempo de inatividade (*zero-downtime*), o comando `REFRESH MATERIALIZED VIEW` deve sempre utilizar a cláusula `CONCURRENTLY`. 

> **Pré-requisito do PostgreSQL:** A execução concorrente exige a presença de ao menos um índice único sem cláusula `WHERE` sobre a visão. Na nossa arquitetura, todas as visões contam com índices únicos dedicados (`source_id` na Camada 1 e `researcher_id` na Camada 2).

#### Roteiro Operacional de Comandos

```sql
-- 1. Atualizar visões da Camada 1 (podem ser executadas em paralelo ou em sequência)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_articles;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_books;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_patents;
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_search_software;

-- 2. Atualizar a visão agregadora da Camada 2 (após término da Camada 1)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_researcher_search;
```

#### Integração no Ciclo de Vida da Aplicação
- **Rotinas Pós-ETL (`scripts/routines/post_hop.sh`):** Disparado ao final dos pipelines de enriquecimento de dados como etapa de consolidação final.
- **Isolamento de Falhas:** Se o refresh de uma fonte da Camada 1 falhar por inconsistência externa, as visões existentes permanecem servindo dados estáveis sem corrupção de cache.

### Matriz de Índices e Aceleração

| Alvo | Tipo de Índice | Justificativa |
| :--- | :--- | :--- |
| `source_id` (Camada 1) | Único (B-Tree) | Habilita atualização concorrente em cada fonte. |
| `researcher_id` (Camada 1) | B-Tree | Torna a Fase 2 (`matched_in`) instantânea para os IDs paginados. |
| `search_vector` (Camada 1 e 2) | GIN | Indexação invertida de alta eficiência para operadores textuais (`@@`). |
| `name` (Camada 2) | GIN (`gin_trgm_ops`) | Habilita busca fonética/aproximada tolerante a erros ortográficos. |
| `graduate_program_ids` (Camada 2)| GIN (Array) | Resolução de filtros de programas de pós-graduação por pertinência (`@>`). |
| `production_years` (Camada 2) | GIN (Array) | Recorte temporal de produções sem dependência de tabelas externas. |


---

## 7. Guia de Evolução: Adicionando Novas Fontes

Para integrar novas competências (ex.: projetos de pesquisa, orientações de pós-graduação, prêmios):

1. **Criação da Visão de Fonte:** Modelar a nova visão materializada aderindo ao contrato de 7 colunas da Camada 1.
2. **Indexação Padrão:** Criar o índice único por `source_id`, índice relacional por `researcher_id` e índice `GIN` no vetor.
3. **Inclusão na Composição:** Adicionar uma linha de união (`UNION ALL`) na visão agregadora da Camada 2.
4. **Agendamento do Refresh:** Adicionar a nova visão ao fluxo de atualização das rotinas de manutenção.

> O contrato de resposta do endpoint e as consultas de consumo permanecem completamente inalterados, preservando a estabilidade da API pública.
