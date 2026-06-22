#!/bin/bash

cd "$(dirname "$0")"
LOG_FILE="./routine.log"

set -e
trap 'echo -e "\n\nErro na linha $LINENO: $BASH_COMMAND" | tee -a "$LOG_FILE"' ERR

handle_error() {
    echo -e "\n\nHouve um erro. Encerrando o script." | tee -a "$LOG_FILE"
    exit 1
}

echo "Executando: soap_lattes.py" | tee -a "$LOG_FILE"
#docker exec iapos-simcc-back-1 python /app/routines/soap_lattes.py || handle_error

echo "Criando diretório XML" | tee -a "$LOG_FILE"
mkdir -p Jade-Extrator-Hop/metadata/dataset/xml || handle_error

echo "Removendo arquivos XML antigos" | tee -a "$LOG_FILE"
rm -f Jade-Extrator-Hop/metadata/dataset/xml/*.xml || handle_error

echo "Copiando arquivos XML do container" | tee -a "$LOG_FILE"
docker cp iapos-simcc-back-1:/app/storage/xml/. Jade-Extrator-Hop/metadata/dataset/xml/ || handle_error

echo "Executando Apache Hop" | tee -a "$LOG_FILE"
docker run --rm \
    --network=iapos-network \
    --env HOP_LOG_LEVEL=Basic \
    --env HOP_FILE_PATH="/files/metadata/dataset/workflow/Index.hwf" \
    --env HOP_PROJECT_CONFIG_FILE_NAME="project-config.json" \
    --env HOP_PROJECT_FOLDER=/files \
    --env HOP_PROJECT_NAME=Jade-Extrator-Hop \
    --env HOP_RUN_CONFIG=local \
    -v "$(pwd)/Jade-Extrator-Hop:/files" \
    apache/hop:2.13.0 || handle_error

echo "Executando: researcher_image.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/researcher_image.py || handle_error

echo "Executando: population.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/population.py || handle_error

echo "Executando: production.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/production.py || handle_error

echo "Executando: researcher_image.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/researcher_image.py || handle_error

echo "Executando: researcher_indprod.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/researcher_indprod.py || handle_error

echo "Executando: program_indprod.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/program_indprod.py || handle_error

echo "Executando: powerBI.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/powerBI.py || handle_error

# echo "Executando: abstract_ai.py" | tee -a "$LOG_FILE"
# docker exec iapos-simcc-back-1 python /app/routines/abstract_ai.py || handle_error

echo "Executando: openAlex.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/openAlex.py || handle_error

echo "Executando: researcher_class.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/researcher_class.py || handle_error

echo "Executando: pog.py" | tee -a "$LOG_FILE"
docker exec iapos-simcc-back-1 python /app/routines/pog.py || handle_error

# echo "Executando: embedding_database.py" | tee -a "$LOG_FILE"
# docker exec iapos-simcc-back-1 python /app/routines/embedding_database.py || handle_error
