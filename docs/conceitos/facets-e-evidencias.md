# Facets, Evidências e Orçamento de Consultas

Um dos pontos centrais da V2 é responder buscas ricas e informativas sem sobrecarregar a infraestrutura do banco de dados.

---

## Catálogo de Opções vs. Facets

É comum iniciantes confundirem esses dois conceitos. A tabela abaixo resume a diferença prática:

| Pergunta | Catálogo de Opções | Facets |
|---|---|---|
| **Pergunta que responde** | *"Quais instituições existem no sistema?"* | *"Dentro deste resultado de busca, quantos pesquisadores há por instituição?"* |
| **Depende da busca atual?** | Não. É uma listagem geral. | **Sim.** As contagens mudam a cada filtro aplicado. |
| **Onde vive na API** | Endpoints próprios: `/v2/institution`, `/v2/graduate_program` | No retorno de `/v2/researcher`, dentro da chave `facets`. |
| **Uso comum no Frontend** | Seletores de filtro, caixas de dropdown, autocompletes. | Painéis laterais com contadores numéricos de refinamento. |

---

## O Conceito de Faceting Disjuntivo

Em interfaces modernas de busca, o usuário precisa ser capaz de refinar e expandir sua pesquisa de forma dinâmica.

!!! question "O Problema do Facet Tradicional (Conjuntivo)"
    Se o usuário busca por "Dengue" e seleciona a instituição **UFBA**, um facet ingênuo aplicaria o filtro da UFBA e mostraria apenas a UFBA no painel lateral com contagem, escondendo todas as outras universidades. O usuário não conseguiria ver que na **UNEB** ou na **UESC** também existem especialistas em Dengue.

### A Solução: Faceting Disjuntivo

O **Faceting Disjuntivo** calcula a contagem de cada campo aplicando todos os filtros da busca atual, **exceto o do próprio campo**:

* Ao calcular o facet de **instituição**: a API ignora o filtro `institution_id` enviado, mas respeita a busca textual `q` e os anos selecionados.
* Ao calcular o facet de **programas**: a API ignora o filtro `graduate_program_id`, mas respeita as instituições e os anos.

Dessa forma, o usuário que selecionou uma instituição continua vendo as opções de outras instituições disponíveis para expandir sua seleção com um clique.

---

## O que são Evidências (Matches)?

Enquanto os facets fornecem **contagens agregadas**, as evidências (**matches**) fornecem **provas concretas por pesquisador**:

* Respondem à pergunta: *"Por que esse pesquisador apareceu nesta busca?"*.
* Indicam quais obras (artigos, livros, softwares) casaram com a palavra-chave.
* Trazem um trecho contextual (snippet) destacando o termo encontrado entre marcadores especiais `[[termo]]`.

```json
{
  "researcher_id": "...",
  "name": "Maria Silva",
  "matches": {
    "total": 4,
    "by_type": { "ARTICLE": 3, "SOFTWARE": 1 },
    "items": [
      {
        "source_type": "ARTICLE",
        "title": "Estudo sobre Dengue e Arboviroses",
        "snippet": "...análise epidemiológica da [[Dengue]] no Nordeste..."
      }
    ]
  }
}
```

---

## O Princípio do Orçamento de Consultas (Query Budget)

Cada requisição à API possui um orçamento rigoroso de consultas ao banco de dados. Isso garante que o tempo de resposta seja previsível e rápido.

### Regras do Orçamento

1. **Busca Básica:** Gasta exatamente **2 consultas** (uma para contar o total de itens e outra para trazer os registros da página atual).
2. **Cada Facet Solicitado:** Adiciona exatamente **1 consulta** focada naquela agregação.
3. **Evidências (`include=matches`):** Adiciona exatamente **2 consultas**.

| O que você pede na URL | Consultas ao Banco |
|---|:---:|
| `GET /v2/researcher` (busca simples) | **2** |
| `GET /v2/researcher?facets=institution` | **3** (2 base + 1 facet) |
| `GET /v2/researcher?facets=institution,year` | **4** (2 base + 2 facets) |
| `GET /v2/researcher?include=matches` | **4** (2 base + 2 matches) |
| `GET /v2/researcher?facets=institution&include=matches` | **5** (2 base + 1 facet + 2 matches) |

!!! tip "Trabalho Pesado Apenas no que Será Exibido"
    A geração de trechos com `ts_headline` e destaque visual de termos é uma operação relativamente custosa. Por isso, as evidências só são calculadas para os pesquisadores que **estão na página atual** (máximo 50 itens), e nunca sobre o universo de milhares de resultados.
