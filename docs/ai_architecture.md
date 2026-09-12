# Arquitetura e Pipeline da MarIA

A **MarIA** é a inteligência artificial conversacional do SIMCC, desenhada especificamente para conectar pesquisadores, gestores públicos e a sociedade ao conhecimento científico produzido no Estado da Bahia.

---

## 🎯 Filosofia de Design e Humanização

Historicamente, ferramentas de busca acadêmica oferecem respostas estritamente tabulares ou mecânicas. A MarIA foi concebida sob os seguintes princípios:

1. **Empatia e Acolhimento**: Comunicação clara, acessível, profissional e humanizada.
2. **Precisão Factual sem Alucinação**: Se os dados da base forem insuficientes ou não atenderem aos critérios de qualidade, o sistema informa isso com transparência em vez de inventar correlações.
3. **Adaptabilidade Contextual**: O tom e a densidade da resposta variam inteligentemente de acordo com a quantidade e a heterogeneidade das evidências científicas encontradas.

---

## 🔄 Fluxo Operacional da Pipeline de IA

A pipeline completa é orquestrada pelo [`MariaService`](file:///home/jaspion/Observatorio/Simcc/simcc-back/src/simcc/services/maria_service.py) e divide-se em 5 estágios bem delineados:

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário / Cliente
    participant Router as MariaRouter (/ai/chat)
    participant Cache as RedisCacheService
    participant Planner as QueryPlanner (LLM)
    participant Search as AISearchService (pgvector)
    participant Maria as MariaPrompt & LLM Synthesis
    participant Tracer as AITracer (JSONL)

    User->>Router: POST /ai/chat/ask (query, session_id)
    Router->>Cache: Verifica Chave Canônica Normalizada
    alt Cache Hit
        Cache-->>Router: Resposta em Cache (JSON ou Eventos SSE)
        Router-->>User: Retorno Imediato (< 50ms)
    else Cache Miss
        Router->>Planner: 1. Planejamento da Consulta (QueryPlan)
        Planner-->>Router: Intenção + Termos Semânticos + Filtros
        Router->>Search: 2. Busca Vetorial Híbrida (pgvector)
        Search-->>Router: Documentos Brutos Recuperados
        Router->>Router: 3. Aplicação da Linha de Corte (Cutoff)
        alt Sem documentos válidos pós-corte
            Router->>Maria: Síntese com Variação Empática (Base em Indexação)
        else Documentos relevantes
            Router->>Maria: 4. Síntese Adaptativa (Variações A, B ou C)
        end
        Maria-->>Router: Resposta Humanizada Gerada
        Router->>Cache: Grava no Redis com TTL configurado
        Router->>Tracer: 5. Emite Log de Tracing JSONL com tempos por estágio
        Router-->>User: Resposta Final (Batch JSON ou SSE Stream)
    end
```

---

## 🧠 Estágios Detalhados

### 1. Planejador de Consultas (`QueryPlanner`)
O usuário expressa sua dúvida de forma livre em linguagem natural. O [`QueryPlanner`](file:///home/jaspion/Observatorio/Simcc/simcc-back/src/simcc/ai/query_planner.py) traduz essa intenção em uma estrutura semântica validada pelo Pydantic ([`QueryPlan`](file:///home/jaspion/Observatorio/Simcc/simcc-back/src/simcc/ai/query_planner.py#L32-L42)) utilizando saída estruturada (*Structured Outputs*) via LangChain e modelo `gpt-4o-mini` com temperatura zero.

A estrutura é composta por:
* **`intent`**: Classificação taxonômica da intenção do usuário;
* **`semantic_query`**: Termos conceituais higienizados para geração de embeddings (removendo saudações e siglas de instituições já filtradas);
* **`filters`**: Objeto [`SearchFilters`](file:///home/jaspion/Observatorio/Simcc/simcc-back/src/simcc/ai/query_planner.py#L8-L30) contendo restrições categóricas, institucionais, temporais e espaciais aplicadas no SQL relacional.

#### Classificação de Intenções (`intent`)

| Intenção (`intent`) | Descrição e Comportamento | Exemplo de Consulta |
|:---|:---|:---|
| `researcher_search` | Busca temático-institucional para localizar ou comparar pesquisadores por área, competência ou instituição. | *"Quais pesquisadores da UNEB trabalham com linguística?"* |
| `production_search` | Busca focada em produções científicas e tecnológicas (artigos, livros, patentes, softwares, relatórios). | *"Quais patentes e registros foram desenvolvidos na UFBA?"* |
| `researcher_profile` | Perfil acadêmico, biografia científica ou trajetória de um indivíduo específico. | *"Quem é Eduardo Manuel de Freitas Jorge e quais são suas áreas de atuação?"* |
| `aggregation` | Consultas analíticas, volumétricas e estatísticas sobre o ecossistema de dados. | *"Quantos artigos foram publicados na Bahia em 2023?"* |
| `general_question` | Saudações, apresentações institucionais ou dúvidas gerais sobre as funcionalidades do SIMCC. | *"Olá MarIA, como você pode me ajudar a explorar a ciência baiana?"* |

#### Filtros Estruturados (`SearchFilters`)

| Campo | Tipo | Descrição | Exemplos Aceitos |
|:---|:---|:---|:---|
| `institutions` | `List[str]` | Lista de siglas ou nomes de instituições mencionadas na consulta. | `["UFBA"]`, `["UNEB", "UEFS"]`, `["UFRB"]`, `["UESB"]` |
| `researcher_name` | `Optional[str]` | Nome específico do pesquisador quando a consulta é direcionada a um indivíduo. | `"Eduardo Manuel de Freitas Jorge"`, `"Adilson"` |
| `production_types` | `List[str]` | Lista de tipos específicos de produção catalogados (vazio busca em todas). | `["ARTICLE"]`, `["PATENT"]`, `["BOOK", "BOOK_CHAPTER"]` |
| `city` | `Optional[str]` | Polo municipal ou cidade do Estado da Bahia mencionada. | `"Salvador"`, `"Feira de Santana"`, `"Ilhéus"` |
| `year_from` | `Optional[int]` | Ano inicial para recorte temporal da busca. | `2019`, `2024` |
| `year_to` | `Optional[int]` | Ano final para recorte temporal da pesquisa. | `2023`, `2026` |

#### Tipos de Produção Suportados (`production_types`)

| Tipo (`production_type`) | Descrição | Termos Comuns Identificados |
|:---|:---|:---|
| `ARTICLE` | Artigos publicados em periódicos científicos | *"artigos", "papers", "publicações"* |
| `BOOK` | Livros completos publicados | *"livros", "obras completas"* |
| `BOOK_CHAPTER` | Capítulos de livros e coletâneas | *"capítulos de livros", "capítulos publicados"* |
| `PATENT` | Patentes e registros de propriedade intelectual | *"patentes", "invenções", "propriedade intelectual"* |
| `SOFTWARE` | Programas de computador e sistemas registrados | *"softwares", "programas", "sistemas"* |
| `REPORT` | Relatórios técnicos e de pesquisa | *"relatórios técnicos", "relatórios de projetos"* |

### 2. Busca Vetorial Híbrida (`AISearchService`)
Integrada ao PostgreSQL 17 utilizando a extensão **`pgvector`**:
* A consulta semântica é convertida em um vetor denso (1536 dimensões);
* É executada a busca por vizinhos mais próximos utilizando a métrica de **distância cosseno** (`<=>`);
* Os filtros relacionais (instituição, grandes áreas) são aplicados de forma combinada no SQL para máxima precisão e performance.

### 3. Linha de Corte de Relevância Semântica (`Cosine Distance Cutoff`)
Para eliminar correspondências forçadas e ruídos de baixa relevância:
* O sistema aplica a condição:
  $$\text{distância cosseno} \le \text{limiar}$$
* Por padrão, adota-se um limiar rigoroso (ex: `0.65`), configurável via `AI_SEARCH_SIMILARITY_THRESHOLD`.
* **Tratamento de Gaps de Qualidade**: Quando nenhum documento ultrapassa o corte de relevância, o sistema **não** envia dados irrelevantes ao modelo de síntese. Em vez disso, aciona a estratégia empática explicando que a base científica baiana está em contínuo processamento e indexação, orientando o usuário a refinar os termos.

### 4. Variações Comportamentais de Resposta (`maria_prompts.py`)
Conforme a natureza dos resultados aprovados na triagem, a MarIA adota uma das 5 variações dinâmicas de prompt:

| Variação | Gatilho de Contexto | Estilo Comportamental |
|:---|:---|:---|
| **Variação A (Grande Volume)** | Mais de 5 registros encontrados | Visão panorâmica executiva, destacando grandes tendências, instituições líderes e eixos principais sem listagens exaustivas e mecânicas. |
| **Variação B (Volume Reduzido)** | Entre 1 e 4 registros encontrados | Análise individual rica e detalhada, contextualizando a produção e a relevância de cada pesquisador ou trabalho catalogado. |
| **Variação C (Heterogênea)** | Múltiplas instituições ou tipos mistos | Estrutura comparativa e categorizada por eixos temáticos ou institucionais, facilitando a navegação multidimensional. |
| **Variação D (Vazia / Pós-Corte)** | Zero registros ou registros descartados | Resposta acolhedora e transparente informando o processamento progressivo da base de dados e sugerindo alternativas de busca. |
| **Variação E (Conversacional)** | Saudações ou perguntas institucionais | Recepção amigável, orientando sobre o papel do SIMCC e convidando o usuário a explorar a produção científica da Bahia. |

### 5. Resiliência e Fallback de Provedor
O sistema trata a ausência ou falha temporária da `OPENAI_API_KEY`:
* Caso a chave não esteja definida ou o provedor esteja indisponível, a API responde graciosamente com **HTTP 503** (ou evento SSE `error`), fornecendo mensagem clara e sem causar crashes na aplicação.
