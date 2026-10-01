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

## Referência dos Facets

### Facets disponíveis

Cada facet é calculado com todos os filtros da requisição, **exceto o do próprio campo**.

| Facet | Filtro que alimenta | `value` | Observações |
|---|---|---|---|
| `institution` | `institution_id` | UUID | Conta cada vínculo: quem está em duas instituições conta nas duas. Traz `acronym`. |
| `graduate_program` | `graduate_program_id` | UUID | Traz `acronym`. |
| `city` | `city_id` | UUID | Cidade de cada vínculo institucional. |
| `identity_territory` | `identity_territory` | texto | Território de identidade de cada vínculo. |
| `graduation` | `graduation` | texto | Maior titulação. |
| `classification` | `classification` | `A+` … `E` | |
| `source_type` | `source_type` | `ARTICLE`, `BOOK`, `BOOK_CHAPTER`, `PATENT`, `SOFTWARE`, `PARTICIPATION_EVENT`, `AREA_SPECIALTY` | Pesquisadores por tipo de obra que conta para a busca (casa com `q` e está no intervalo de anos). Funciona com ou sem `q`. |
| `year` | `year_start` / `year_end` | ano | Com `q` ou `source_type`, conta os anos das obras que contam para a busca; sem eles, os anos de qualquer produção. Não tem `selected` (é um intervalo). |

### Formato da resposta

Cada facet solicitado vira uma chave em `facets`, sempre com o mesmo formato:

```json
"facets": {
  "institution": {
    "total": 34,
    "items": [
      { "value": "<uuid>", "label": "Universidade Federal da Bahia", "acronym": "UFBA", "count": 42, "selected": false },
      { "value": "<uuid>", "label": "Universidade do Estado da Bahia", "acronym": "UNEB", "count": 17, "selected": true }
    ]
  }
}
```

| Campo | Significado |
|---|---|
| `total` | Quantos valores distintos têm pelo menos um pesquisador. Use para exibir "ver todas (34)" quando `total > items.length`. |
| `items[].value` | O valor a enviar no filtro correspondente (ex.: `institution_id=<value>`). |
| `items[].label` | Texto de exibição (nome completo). |
| `items[].acronym` | Sigla, quando o valor for uma entidade que tenha uma. `null` em `year` e `source_type`. |
| `items[].count` | Quantos pesquisadores do resultado atual possuem esse valor. |
| `items[].selected` | `true` quando o valor já está aplicado no filtro da requisição. |

### Regras de montagem da lista

1. **Ordenação:** do maior `count` para o menor. Empates são resolvidos pelo nome (`year` desempata do ano mais recente para o mais antigo), então a ordem é estável entre requisições.
2. **Limite:** até `facet_limit` itens (padrão 20, máximo 100).
3. **Selecionados sempre presentes** (todos, exceto `year`): um valor enviado no filtro volta com `selected: true` mesmo que esteja fora do limite, ao final da lista. Se os outros filtros zerarem o resultado dele, ele volta com `count: 0`. Assim o checkbox marcado nunca some da tela.
4. Valores com `count: 0` só aparecem quando selecionados, e **não** entram em `total`.

!!! example "Receita para a barra lateral"
    1. Busca inicial: `GET /v2/researcher?q=dengue&facets=institution,graduate_program`.
    2. Renderize um checkbox por item, marcado conforme `selected`, exibindo `acronym` (ou `label`) e `count`.
    3. Ao marcar ou desmarcar, refaça a chamada com o conjunto atual de `institution_id` / `graduate_program_id`. Não é preciso guardar estado de contagem no frontend.
    4. Se `total > items.length`, ofereça "ver todas", repetindo a chamada com `facet_limit` maior.

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

1. **Busca Básica:** Gasta exatamente **3 consultas** (uma para contar o total de itens, outra para trazer os registros da página atual e uma para os [vínculos institucionais](vinculos-institucionais.md) desses pesquisadores).
2. **Cada Facet Solicitado:** Adiciona exatamente **1 consulta** focada naquela agregação.
3. **Evidências (`include=matches`):** Adiciona exatamente **2 consultas**.

| O que você pede na URL | Consultas ao Banco |
|---|:---:|
| `GET /v2/researcher` (busca simples) | **3** |
| `GET /v2/researcher?facets=institution` | **4** (3 base + 1 facet) |
| `GET /v2/researcher?facets=institution,year` | **5** (3 base + 2 facets) |
| `GET /v2/researcher?include=matches` | **5** (3 base + 2 matches) |
| `GET /v2/researcher?facets=institution&include=matches` | **6** (3 base + 1 facet + 2 matches) |
| Qualquer busca repetida (acerto no [cache](cache.md)) | **0** |

!!! tip "Trabalho Pesado Apenas no que Será Exibido"
    A geração de trechos com `ts_headline` e destaque visual de termos é uma operação relativamente custosa. Por isso, as evidências só são calculadas para os pesquisadores que **estão na página atual** (máximo 50 itens), e nunca sobre o universo de milhares de resultados.
