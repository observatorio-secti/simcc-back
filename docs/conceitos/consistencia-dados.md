# Consistência de Dados

O módulo compara os totais do banco antes e depois de uma carga e registra
variações que precisam ser analisadas.

---

## Escopo atual

O MVP acompanha as seguintes métricas:

| Chave | Descrição |
|---|---|
| `researchers_total` | Pesquisadores ativos (`status = true`). |
| `teachers_total` | Pesquisadores docentes (`docente = true`). |
| `graduate_programs_total` | Programas de pós-graduação. |
| `cnpq_fellows_total` | Pesquisadores com bolsa positiva em registros de fomento CNPq. |
| `articles_total` | Artigos em periódicos. |
| `books_total` | Livros. |
| `book_chapters_total` | Capítulos de livros. |
| `patents_total` | Patentes. |
| `softwares_total` | Softwares. |
| `brands_total` | Marcas. |
| `technical_reports_total` | Relatórios técnicos. |
| `guidance_total` | Orientações. |
| `event_participation_total` | Participações em eventos. |
| `research_projects_total` | Projetos de pesquisa. |
| `publishing_total` | Textos publicados em revistas ou jornais. |
| `works_in_events_total` | Trabalhos publicados em eventos. |
| `periodicals_total` | Revistas cadastradas no catálogo. |
| `jcr_records_total` | Registros importados na tabela JCR. |
| `jcr_articles_total` | Artigos vinculados a um fator JCR. |
| `jcr_citations_total` | Soma das citações dos periódicos JCR. |
| `jcr_journal_articles_total` | Soma de artigos declarada pelos periódicos JCR. |
| `openalex_profiles_total` | Pesquisadores com perfil OpenAlex. |
| `openalex_works_total` | Soma de trabalhos dos perfis OpenAlex. |
| `openalex_articles_total` | Artigos com registro OpenAlex. |
| `openalex_researcher_citations_total` | Soma de citações dos perfis OpenAlex. |
| `openalex_article_citations_total` | Soma de citações dos artigos OpenAlex. |
| `openalex_i10_total` | Soma do índice i10 dos perfis OpenAlex. |

Todas são calculadas nos escopos:

* `GLOBAL`: total geral.
* `INSTITUTION`: total por instituição.

Pesquisadores por instituição usam os vínculos de
`researcher_institution`. Programas usam `graduate_program.institution_id`.
O acompanhamento de grupos de pesquisa será feito pelo backend separado
mantido pela equipe responsável por essa ingestão.

As contagens de livros e capítulos são separadas no contrato; o frontend pode
somá-las para exibir “Livros e capítulos”. JCR, OpenAlex e outros indicadores
bibliométricos médios não fazem parte do snapshot. As métricas JCR são globais;
as métricas OpenAlex também são calculadas por instituição, usando o vínculo
do pesquisador.

`cnpq_fellows_total` considera registros de `foment` com
`scholarship_quantity > 0` e instituição/programa contendo “CNPq”. Essa regra
deve ser confirmada com a equipe quando a base oficial for disponibilizada.

Médias de fator de impacto e índice H não entram no snapshot padrão, pois podem
oscilar sem representar perda ou ganho de registros.

---

## Comparação

O percentual é calculado pelo backend:

```text
((after_value - before_value) / before_value) * 100
```

Limites padrão:

| Direção | Limite | Alerta |
|---|---:|---|
| Redução | `5%` | `variation_percent <= -5` |
| Aumento | `10%` | `variation_percent >= 10` |

Os limites podem ser enviados na finalização da carga e ficam armazenados no
resultado.

### Estados

| Estado | Significado |
|---|---|
| `NORMAL` | Variação dentro dos limites. |
| `WARNING` | Variação fora de um dos limites. |
| `NEW_SCOPE` | `before_value = 0` e `after_value > 0`. |
| `UNCHANGED` | Não houve alteração, inclusive quando ambos são zero. |

Uma redução de um valor positivo para zero é `WARNING` com variação de `-100%`.
`NEW_SCOPE` não gera alerta automático.

---

## Persistência

O módulo usa três tabelas:

| Tabela | Finalidade |
|---|---|
| `data_load_run` | Execução da carga, status, origem e horários. |
| `data_snapshot_metric` | Fotografia `BEFORE` ou `AFTER` de cada métrica. |
| `data_consistency_result` | Resultado consolidado da comparação. |

O histórico institucional preserva o nome da instituição capturado no momento
da carga. A referência à instituição usa `ON DELETE SET NULL`.

Uma carga pode ter status `VALIDATED` mesmo contendo métricas `WARNING`; o
alerta pertence ao resultado, não à execução.

---

## API

Os endpoints estão registrados na aplicação v1. O prefixo pode mudar conforme
o proxy de publicação.

### Relatórios

| Método | Endpoint | Uso |
|---|---|---|
| `GET` | `/data-consistency/latest` | Último relatório validado. |
| `GET` | `/data-consistency/history` | Histórico de execuções. |
| `GET` | `/data-consistency/loads/latest` | Última execução por tipo de carga. |

`/history` aceita os filtros `load_type`, `status`, `date_from`, `date_to` e
`limit`.

`/latest` retorna `404` quando ainda não existe carga validada.

### Integração com cargas

| Método | Endpoint | Uso |
|---|---|---|
| `POST` | `/internal/data-consistency/loads` | Inicia carga e captura `BEFORE`. |
| `POST` | `/internal/data-consistency/loads/{load_id}/finish` | Captura `AFTER` e compara. |
| `POST` | `/internal/data-consistency/loads/{load_id}/fail` | Registra falha. |

Endpoints internos exigem:

```text
X-Internal-API-Key: <INTERNAL_API_KEY>
```

A integração com a rota de upload ainda não está implementada neste backend. Antes
de conectar o ciclo, deve confirmar a rota/serviço e como identificar
que os dados foram gravados ou que o processamento falhou.

O fluxo esperado para cada ingestão é:

```text
POST /loads
executar carga
POST /loads/{id}/finish
```

O `start` deve ocorrer antes das alterações no banco; `finish`, depois da
confirmação de que a ingestão foi concluída; e `/fail`, se ela falhar. Se o
upload iniciar um processamento assíncrono, o pipeline precisa aguardar um
callback ou consultar um status final antes de chamar `finish`.

O corpo de `/loads` é:

```json
{
  "load_type": "<TIPO_DE_CARGA_CONFIRMADO>",
  "trigger_source": "<ORIGEM_CONFIRMADA>"
}
```

O corpo opcional de `/finish` é:

```json
{
  "lower_tolerance": 5,
  "upper_tolerance": 10
}
```

Os endpoints internos são destinados ao pipeline, não ao frontend.

---

## Resposta do relatório

`GET /data-consistency/latest` retorna:

```json
{
  "load": {},
  "summary": {},
  "metrics": []
}
```

### `load`

| Campo | Descrição |
|---|---|
| `id` | Identificador da execução. |
| `load_type` | Tipo da carga acordado e informado pelo pipeline. |
| `status` | `RUNNING`, `VALIDATED` ou `FAILED`. |
| `trigger_source` | Origem, como `MANUAL`, `HOP` ou `SCHEDULED`. |
| `started_at` | Data e hora de início. |
| `finished_at` | Data e hora de término ou `null`. |
| `error_detail` | Detalhe da falha ou `null`. |

### `summary`

| Campo | Descrição |
|---|---|
| `total_metrics` | Total de resultados comparados. |
| `warnings` | Resultados com `is_warning = true`. |
| `normal` | Resultados `NORMAL`. |
| `new_scopes` | Resultados `NEW_SCOPE`. |

### `metrics`

| Campo | Descrição |
|---|---|
| `metric_key` | Chave da métrica. |
| `scope` | `GLOBAL` ou `INSTITUTION`. |
| `institution_id` | ID da instituição ou `null`. |
| `institution_name` | Nome da instituição ou `null`. |
| `before_value` | Valor antes da carga. |
| `after_value` | Valor depois da carga. |
| `absolute_difference` | `after_value - before_value`. |
| `variation_percent` | Variação calculada ou `null` em `NEW_SCOPE`. |
| `lower_threshold` | Limite de redução utilizado. |
| `upper_threshold` | Limite de aumento utilizado. |
| `status` | Estado da comparação. |
| `is_warning` | Indica se a linha deve ser destacada. |
| `warning_reason` | Motivo do alerta ou `null`. |

O frontend deve usar `is_warning`, `status` e `variation_percent` recebidos do
backend. Não é necessário recalcular a variação.

---

## Configuração

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | Banco principal da aplicação. |
| `INTERNAL_API_KEY` | Chave dos endpoints internos. |

O `.env` local deve usar credenciais locais. Credenciais do ambiente oficial
não devem ser commitadas nem compartilhadas no repositório.

---

## Próximas etapas

* Confirmar a rota de upload, os tipos de carga e o sinal de sucesso/falha.
* Implementar o envio diário de e-mails.
* Definir autenticação de produção para frontend e serviços internos.
* Avaliar médias bibliométricas em um painel separado, fora dos alertas.
