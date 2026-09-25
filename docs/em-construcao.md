# Recursos em Construção

Esta seção lista melhorias e módulos planejados para as próximas versões da API V2 do SIMCC.

---

## Roadmap da V2

| Recurso / Módulo | Descrição Prevista | Status |
|---|---|:---:|
| **Cache Distribuído (Redis)** | Cache opt-in para buscas frequentes e contagens de facets, com invalidação atrelada ao refresh das visões materializadas. | *Em construção* |
| **Paginação por Cursor (Keyset)** | Alternativa de paginação para grandes volumes de dados que não degrada a performance em offsets elevados (`page > 500`). | *Em construção* |
| **Filtros Avançados de Produção** | Filtros estruturados para estratos Qualis, tipo de produção bibliográfica e subáreas de conhecimento do CNPq na V2. | *Em construção* |
| **Exportação em Lote** | Endpoints dedicados para download de relatórios consolidados em formatos CSV, XLSX e JSON. | *Em construção* |
| **Painel de Saúde das MVs** | Métricas de monitoramento e alertas automáticos sobre tempo de execução do refresh e defasagem dos dados. | *Em construção* |
