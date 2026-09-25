#!/bin/bash
set -e

docker compose exec api ./scripts/routines/pre_hop.sh

docker compose run --rm -e HOP_FILE_PATH=/files/jade-extrator/workflows/Index.hwf hop

docker compose exec api ./scripts/routines/post_hop.sh

# Atualiza as visões materializadas de busca e invalida o cache da v2
docker compose exec api python scripts/routines/run_routine.py refresh_search_views.py

# Garantia: invalida o cache mesmo que o Redis tenha falhado durante o refresh
docker compose exec redis redis-cli INCR simcc:v2:search:generation