# SIMCC V2 - Documentação e Padrões

Esta documentação aborda algo menos técnico: os conceitos fundamentais, as regras de implementação e os padrões de uso dos recursos do sistema.

Para consultar endpoints, parâmetros e esquemas de resposta:
* Acesse a rota `/swagger` no ambiente da aplicação.

---

## Bem-vindo ao SIMCC V2

A versão 2 (V2) da API do SIMCC foi projetada para atender ao **Observatório e Inteligência Científica do Estado da Bahia** com altíssimo desempenho, escalabilidade e facilidade de manutenção.

Ela foi desenhada para substituir consultas dinâmicas lentas por uma arquitetura moderna baseada em **Visões Materializadas**, permitindo consultas textuais instantâneas sobre centenas de milhares de produções acadêmicas sem sobrecarregar o banco de dados.

---

## Os 4 Pilares da V2

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│     1. Orçamento de Queries     │     │   2. Visões Materializadas      │
│  Número previsível de consultas │     │  Dados consolidados e indexados │
│  (2 queries na busca básica)    │     │  com índices invertidos GIN     │
└─────────────────────────────────┘     └─────────────────────────────────┘

┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│     3. Recursos Opt-in          │     │     4. Validação Defensiva      │
│  Trabalho pesado (matches e     │     │  Entradas desconhecidas geram   │
│  facets) roda apenas sob demanda│     │  HTTP 422 imediato              │
└─────────────────────────────────┘     └─────────────────────────────────┘
```

1. **Orçamento Rigoroso de Consultas:** Cada requisição tem um custo fixo e previsível. Nada roda no banco sem ser explicitamente solicitado.
2. **Visões Materializadas em Duas Camadas:** O banco pré-calcula a relação entre documentos e perfis, viabilizando buscas textuais completas e instantâneas.
3. **Trabalho Pesado Apenas no que é Exibido:** Geração de snippets destacados e relevâncias avançadas rodam exclusivamente sobre os itens da página atual (máximo 50 itens).
4. **Validação Defensiva:** Parâmetros desconhecidos ou regras violadas são barrados antes de tocarem o banco de dados.

---

## Navegação Rápida

Explore a documentação através das seções abaixo:

### [Conceitos da V2](conceitos/arquitetura.md)
* [**Arquitetura e Visões Materializadas**](conceitos/arquitetura.md): Como as duas camadas de dados funcionam e por que usamos MVs.
* [**Filtros Padrões e Mecanismo de Busca**](conceitos/filtros-e-busca.md): Tabela de parâmetros padrão, regras lógicas e fórmula de relevância.
* [**Facets, Evidências e Orçamento**](conceitos/facets-e-evidencias.md): Faceting disjuntivo, evidências com snippets e limites de consultas.

### [Guia de Contribuição](guia-contribuicao/index.md)
* [**1. Criação de Rotinas e Serviços**](guia-contribuicao/rotinas.md): Como organizar regras de negócio com checklist de qualidade.
* [**2. Criação de Endpoints**](guia-contribuicao/endpoints.md): Passo a passo para criar rotas FastAPI com checklist de validação.
* [**3. Criação de Testes**](guia-contribuicao/testes.md): Como garantir isolamento, uso de factories e checklist de testes.

### [Recursos em Construção](em-construcao.md)
* [**Roadmap da V2**](em-construcao.md): Recursos previstos para as próximas iterações (Cache, Paginação por Cursor, etc.).