# pipeline/constants.py
"""
Constantes de domínio compartilhadas entre os módulos do projeto.

Constantes de taxonomia específica (ex: nomes de área do CNPq) não pertencem
aqui — ficam nos arquivos de config em data/taxonomies/*.json e são carregadas
via TaxonomyConfig.
"""

# Valores do atributo "origin" nos nós do grafo NetworkX
# Centralizados aqui para evitar magic strings espalhadas pelo código.
TAXONOMY_ORIGIN = "TAXONOMY"
TOPIC_ORIGIN = "TOPIC"
SUBTOPIC_ORIGIN = "SUBTOPIC"