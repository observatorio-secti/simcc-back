from typing import List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    institutions: List[str] = Field(
        default_factory=list,
        description="Lista de instituições ou siglas mencionadas, ex: ['UFBA'], ['UNEB'], ['UFBA', 'UNEB'], ['UEFS'], ['UESB'], ['UFRB']",
    )
    researcher_name: Optional[str] = Field(
        None,
        description="Nome específico de um pesquisador se a pergunta for sobre alguém em particular, ex: 'Eduardo Manuel de Freitas Jorge'",
    )
    production_types: List[str] = Field(
        default_factory=list,
        description="Tipos de produções solicitadas: 'ARTICLE' (artigos em periódicos), 'BOOK' (livros), 'BOOK_CHAPTER' (capítulos de livros), 'PATENT' (patentes/registros), 'SOFTWARE' (programas de computador), 'REPORT' (relatórios técnicos)",
    )
    city: Optional[str] = Field(
        None, description="Nome da cidade, ex: 'Salvador', 'Feira de Santana'"
    )
    year_from: Optional[int] = Field(
        None, description='Ano de início para o filtro temporal'
    )
    year_to: Optional[int] = Field(
        None, description='Ano de término para o filtro temporal'
    )


class QueryPlan(BaseModel):
    intent: str = Field(
        description="Intenção principal da consulta: 'production_search' (busca por produções científicas/tecnológicas: artigos, livros, patentes, softwares, relatórios), 'researcher_profile' (perfil de indivíduo específico), 'researcher_search' (busca temática/institucional de pesquisadores), 'aggregation' (estatísticas/contagem) ou 'general_question' (saudações e dúvidas gerais sobre o sistema)."
    )
    semantic_query: str = Field(
        description="Termos semânticos e conceituais para busca vetorial. Remova saudações e nomes de instituições. Mantenha os tópicos, áreas, temas, patentes ou títulos. Se a consulta for genérica sem tema (ex: 'Quais patentes existem?'), deixe uma string temática representativa ou vazia."
    )
    filters: SearchFilters = Field(
        description='Filtros estruturados extraídos da consulta.'
    )


PLANNER_SYSTEM_PROMPT = """
Você é o orquestrador de busca e planejamento de consultas (Query Planner) da MarIA, a assistente científica de dados de pesquisadores da Bahia.
Sua missão é converter a pergunta em linguagem natural do usuário em um plano estruturado de busca (`QueryPlan`).

Regras de Classificação de Intenção (`intent`):
1. `production_search`: O usuário quer encontrar artigos, livros, capítulos, patentes, softwares ou relatórios técnicos.
2. `researcher_profile`: O usuário pergunta sobre um indivíduo específico (ex: "Quem é Eduardo Manuel...", "Qual o currículo de Fulano").
3. `researcher_search`: O usuário quer localizar ou comparar pesquisadores por área, tema, instituição ou experiência.
4. `aggregation`: Perguntas quantitativas ("Quantos artigos foram publicados em 2023?").
5. `general_question`: Cumprimentos, saudações ou dúvidas gerais sobre como o SIMCC funciona.

Regras para Filtros e Tipos de Produção (`production_types`):
- Se o usuário mencionar artigos, adicione 'ARTICLE'.
- Se mencionar livros, adicione 'BOOK'.
- Se mencionar capítulos, adicione 'BOOK_CHAPTER'.
- Se mencionar patentes ou propriedade intelectual, adicione 'PATENT'.
- Se mencionar softwares, programas ou sistemas desenvolvidos, adicione 'SOFTWARE'.
- Se mencionar relatórios técnicos ou de pesquisa, adicione 'REPORT'.
- Se pedir "produções" no geral sem especificar tipo, deixe `production_types: []` (para buscar em todas).

Exemplos:
- "Quais artigos foram publicados sobre leishmaniose ou imunologia?"
  -> intent: "production_search", production_types: ["ARTICLE"], institutions: [], semantic_query: "leishmaniose imunologia infecção celular"

- "Quais patentes e registros foram desenvolvidos na UFBA?"
  -> intent: "production_search", production_types: ["PATENT"], institutions: ["UFBA"], semantic_query: ""

- "Livros e capítulos publicados sobre história da Bahia"
  -> intent: "production_search", production_types: ["BOOK", "BOOK_CHAPTER"], institutions: [], semantic_query: "história da Bahia historiografia memória"

- "Softwares e programas desenvolvidos em inteligência artificial na UNEB"
  -> intent: "production_search", production_types: ["SOFTWARE"], institutions: ["UNEB"], semantic_query: "inteligência artificial sistemas de computação"

- "Relatórios técnicos de projetos de pesquisa na área de saúde"
  -> intent: "production_search", production_types: ["REPORT"], institutions: [], semantic_query: "saúde pública epidemiologia projetos"

- "Quais pesquisadores da UNEB trabalham com linguística?"
  -> intent: "researcher_search", production_types: [], institutions: ["UNEB"], semantic_query: "linguística letras vernáculas"
"""


class QueryPlanner:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        if self.api_key:
            self.llm = ChatOpenAI(
                api_key=api_key, model='gpt-4o-mini', temperature=0
            )
            self.structured_llm = self.llm.with_structured_output(QueryPlan)
            self.prompt = ChatPromptTemplate.from_messages([
                ('system', PLANNER_SYSTEM_PROMPT),
                ('human', '{question}'),
            ])
            self.chain = self.prompt | self.structured_llm
        else:
            self.chain = None

    async def plan(self, question: str) -> QueryPlan:
        if not self.chain:
            from simcc.ai.exceptions import AIServiceUnavailableException

            raise AIServiceUnavailableException()
        return await self.chain.ainvoke({'question': question})
