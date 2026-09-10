#!/bin/bash

set -e

ROUTINES=(
    "sync_admin/sync_graduate_programs.py"
    "sync_admin/sync_rating_programs.py"
    "sync_admin/sync_gp_researchers.py"
    "soap_lattes.py"
)

total=${#ROUTINES[@]}

for i in "${!ROUTINES[@]}"; do
    current=$((i + 1))

    echo "[PRE_HOP] $current/$total Running ${ROUTINES[$i]}..."

    python scripts/routines/run_routine.py "${ROUTINES[$i]}"
done