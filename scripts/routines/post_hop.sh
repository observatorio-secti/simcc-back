#!/bin/bash

set -e

ROUTINES=(
    "pog.py"
    "researcher_production.py"
    "research_dictionaries.py"
    "get_lattes_10.py"
    "researcher_indprod.py"
    "graduate_program_indprod.py"
    "abstract_ai.py"
    "get_openAlex.py"
    "search_terms.py"
    "researcher_classification.py"
    "sync_research_lines.py"
    "refresh_search_views.py"
)

total=${#ROUTINES[@]}

for i in "${!ROUTINES[@]}"; do
    current=$((i + 1))

    echo "[POST_HOP] $current/$total Running ${ROUTINES[$i]}..."

    python scripts/routines/run_routine.py "${ROUTINES[$i]}"
done