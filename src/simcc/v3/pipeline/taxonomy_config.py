"""
taxonomy_config.py — Configuração de domínio para uma taxonomia.

TaxonomyConfig descreve os parâmetros que variam entre taxonomias
(CNPq, ODS, arboviroses, etc.) e são usados por graph_populate,
graph_topic_integrator e topic_hierarchizer para produzir grafos e prompts
agnósticos ao domínio.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TaxonomyConfig:
    """
    Parâmetros de uma taxonomia específica.

    frozen=True — imutável após criação, seguro para passar entre módulos
    sem risco de mutação acidental.

    Três campos alimentam o LLM em topic_hierarchizer:
    - domain_description: frase curta usada nos Field.description dos schemas Pydantic.
    - area_examples: nomes curtos das áreas, também nos Field.description.
    - taxonomy_context: texto rico injetado no system prompt — vazio para taxonomias
      que o LLM já conhece bem (ex: CNPq), detalhado para taxonomias menos conhecidas
      (ex: ODS, arboviroses).
    """

    # Identidade
    name: str
    """Nome curto da taxonomia. Ex: 'CNPq', 'ODS', 'Arboviroses'."""

    domain_description: str          
    """
    Descrição do domínio para o LLM.
    Ex: 'taxonomia acadêmica brasileira do CNPq'.
    Usada no system prompt e nas descrições dos campos Pydantic.
    """

    area_examples: list[str]
    """
    Exemplos de áreas válidas para o domínio.
    Injetados nas descriptions dos campos para guiar o LLM.
    Ex: ['Ciência da Computação', 'Saúde Coletiva'] para CNPq.
        ['Saúde e Bem-Estar', 'Educação de Qualidade'] para ODS.
    """

    taxonomy_context: str = ""
    """
    Texto descritivo rico sobre o domínio, injetado no system prompt.
    Vazio para taxonomias que o LLM conhece bem (ex: CNPq).
    Detalhado para taxonomias menos conhecidas (ex: ODS, arboviroses),
    onde cada área precisa ser descrita para o LLM classificar corretamente.
    """

    # Atributos dos nós da taxonomia base no grafo
    origin_label: str = "TAXONOMY"
    """
    Valor do atributo 'origin' nos nós da taxonomia base.    
    """

    node_color: str = "#97C2FC"      # cor padrão dos nós da taxonomia
    edge_relation: str = "CHILD_OF" # rótulo das arestas hierárquicas

    # Estrutura hierárquica
    area_filter_layer: int = 1
    """
    Layer cujos nós aparecem no filtro de áreas da UI.
    Para CNPq é 1 (Grande Área). Para outras taxonomias pode ser diferente.
    """

    @classmethod
    def from_dict(cls, data: dict) -> TaxonomyConfig:
        """
        Instancia um TaxonomyConfig a partir de um dicionário.
        Ponto de entrada para configs carregadas de JSON, banco de dados
        ou formulário do frontend.

        Se o JSON contém 'areas_detail' (dict estruturado por área), deriva
        automaticamente 'area_examples' e 'taxonomy_context' a partir dele.
        Se não, usa 'area_examples' diretamente e 'taxonomy_context' como string.
        """
        for required in ("name", "domain_description"):
            if required not in data:
                raise ValueError(
                    f"Campo obrigatório ausente no config da taxonomia: '{required}'"
                )
        
        areas_detail: dict = data.get("areas_detail", {})

        if areas_detail:
            area_examples = [v["title"] for v in list(areas_detail.values())[:3]]
            taxonomy_context = "\n\n".join(
                f"{data['name']} {key}:\nTítulo: {val['title']}\nDescrição: {val['description']}"
                for key, val in areas_detail.items()
            )
        else:
            area_examples = data.get("area_examples", [])
            taxonomy_context = data.get("taxonomy_context", "")
 
        return cls(
            name=data["name"],
            domain_description=data["domain_description"],
            area_examples=area_examples,
            taxonomy_context=taxonomy_context,
            origin_label=data.get("origin_label", "TAXONOMY"),
            node_color=data.get("node_color", "#97C2FC"),            
            edge_relation=data.get("edge_relation", "CHILD_OF"),            
            area_filter_layer=data.get("area_filter_layer", 1),
        )
    
    @classmethod
    def from_json(cls, path: Path) -> TaxonomyConfig:
        """
        Carrega um TaxonomyConfig de um arquivo JSON.
        Conveniente para configs locais em data/taxonomies/.
        """
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))