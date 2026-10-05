#!/bin/bash
set -e

SERVICE_API="${SERVICE_API:-simcc-back}"

docker compose up -d "$SERVICE_API"

exec_api() {
  docker compose exec "$SERVICE_API" python "/app/routines/$@"
}

echo "--- Registrando Snapshot Pré-Carga (Auditoria) ---"
exec_api data_quality_monitor.py --snapshot

echo "--- Início da Rotina SOAP_LATTES ---"

exec_api soap_lattes.py

echo "--- SOAP_LATTES concluído ---"

docker compose --profile extração run --rm hop

ROTINES=(
  population.py
  production.py
  pog.py
  researcher_image.py
  researcher_indprod.py
  program_indprod.py
  powerBI.py
  abstract_ai.py
  openAlex.py
  search_terms.py
)

echo "--- Início das rotinas pós-extração ---"

for r in "${ROTINES[@]}"; do
  exec_api "$r"
done

echo "--- Executando Auditoria de Variação e Integridade ---"
exec_api data_quality_monitor.py --audit

echo "--- Rotina Concluída ---"
