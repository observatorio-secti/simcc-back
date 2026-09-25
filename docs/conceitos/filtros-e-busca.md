# Filtros Padrões e Mecanismo de Busca

A V2 padroniza a forma como filtros são recebidos e combinados para garantir que a navegação do usuário seja rápida, intuitiva e sem surpresas.

---

## Tabela de Filtros Padrões da V2

Todos os endpoints de busca de pesquisadores e catálogos seguem a mesma convenção de parâmetros:

| Parâmetro | Tipo | Exemplo | Descrição e Regras |
|---|---|---|---|
| `q` | Texto | `?q=inteligência artificial` | Termo ou frase de busca textual. Ignora acentuação (`pt_unaccent`) e maiúsculas/minúsculas. |
| `institution_id` | Lista de UUIDs | `?institution_id=<uuid>&institution_id=<uuid>` | Filtra pesquisadores vinculados às instituições indicadas. |
| `graduate_program_id` | Lista de UUIDs | `?graduate_program_id=<uuid>` | Filtra pesquisadores associados a programas de pós-graduação. |
| `year_start` | Número inteiro | `?year_start=2018` | Ano inicial do intervalo de produção. |
| `year_end` | Número inteiro | `?year_end=2024` | Ano final do intervalo de produção. Deve ser maior ou igual a `year_start`. |
| `page` | Número inteiro | `?page=1` | Número da página solicitada (mínimo 1, padrão 1). |
| `per_page` | Número inteiro | `?per_page=20` | Quantidade de itens por página (entre 1 e 100, padrão 20). |
| `sort_by` | Texto fixo | `?sort_by=relevance` | Campo de ordenação: `name`, `id` ou `relevance`. |
| `sort_order` | Texto fixo | `?sort_order=desc` | Sentido da ordenação: `asc` (crescente) ou `desc` (decrescente). |
| `facets` | Lista de textos | `?facets=institution,year` | Facets opt-in solicitados para compor painéis laterais de contagem. |
| `include` | Lista de textos | `?include=matches` | Recursos adicionais opt-in (ex.: trechos de evidência com destaque). |
| `matches_limit` | Número inteiro | `?matches_limit=3` | Quantidade máxima de evidências por pesquisador (1 a 5, padrão 3). |

---

## Regras de Combinação de Filtros

Para quem desenvolve a interface ou consome a API, as regras de combinação são simples e consistentes:

```
(Instituição A OU Instituição B) 
               E 
(Programa X OU Programa Y) 
               E 
(Produção no intervalo de Anos)
```

1. **Dentro do mesmo filtro (Multivalorado):** A combinação é do tipo **OU (OR)**. Se o usuário seleciona duas instituições, ele deseja ver pesquisadores que estejam na primeira *ou* na segunda.
2. **Entre filtros diferentes:** A combinação é do tipo **E (AND)**. Se o usuário seleciona uma instituição e um intervalo de anos, o sistema busca pesquisadores que atendam à instituição *e* tenham publicado naquele intervalo.
3. **Validação Defensiva (Parâmetros Desconhecidos):** Qualquer parâmetro enviado na URL que não pertença à lista de parâmetros conhecidos retorna imediatamente erro **HTTP 422 (Entidade Não Processável)**. Isso evita que erros de digitação no frontend passem despercebidos.

---

## Como Funciona o Ranking de Relevância

Quando o usuário busca por um termo e solicita ordenação por relevância (`sort_by=relevance`), a API utiliza uma fórmula equilibrada que valoriza tanto a afinidade do perfil quanto a autoridade por volume de produção:

$$\text{Score} = (\text{Score do Perfil} \times 1.5) + \text{Densidade da Melhor Produção} + \ln(\text{Total de Produções Casadas} + 1)$$

### O que compõe essa pontuação?

* **Score do Perfil ($\times 1.5$):** Avalia se o termo buscado está no nome do pesquisador (com peso maior) ou no seu resumo acadêmico (abstract) do Lattes.
* **Densidade da Melhor Produção:** Pontuação atribuída pelo motor de busca (`ts_rank`) para a obra onde o termo aparece com maior destaque no título.
* **Volume de Produções Casadas ($\ln(N + 1)$):** Premia pesquisadores com ampla produção sobre o tema. Uma escala logarítmica garante que quem tem 30 artigos sobre o assunto apareça à frente de quem tem apenas 1, sem que essa diferença matemática distorça os demais fatores.

### Direção de Ordenação Inteligente

* Ao ordenar por `sort_by=relevance`, a ordenação padrão assumida pela API é **decrescente (`desc`)**, apresentando os pesquisadores mais relevantes no topo da lista.
* Ao ordenar por `sort_by=name`, a ordenação padrão é **crescente (`asc`)**, organizando a listagem em ordem alfabética de A a Z.
