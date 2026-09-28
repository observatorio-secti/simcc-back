FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    PATH="/opt/poetry/bin:/opt/pysetup/.venv/bin:$PATH"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3

WORKDIR $PYSETUP_PATH

FROM base AS builder

COPY pyproject.toml poetry.lock ./

RUN poetry lock --no-interaction && poetry install --only main --no-root

# O BERTopic declara sentence-transformers como dependência, mas nunca importa o
# pacote: o pipeline usa FastEmbed (ONNX). Removendo a cadeia PyTorch da imagem
# (torch + os ~3 GB de runtime CUDA e triton que ele arrasta), já que nada mais
# no backend a utiliza. São ~4 GB que só custam download e boot, sem ganho.
RUN set -eu; \
    remove_pkgs="sentence-transformers torch torchvision torchaudio triton sympy"; \
    remove_pkgs="$remove_pkgs $(pip list --format=freeze | cut -d= -f1 | grep -i '^nvidia-' || true)"; \
    pip uninstall -y $remove_pkgs > /dev/null; \
    find /opt/pysetup/.venv -maxdepth 4 \( -iname 'torch*' -o -iname 'triton*' -o -iname 'nvidia*' \) \
         -exec rm -rf {} + 2> /dev/null || true; \
    pip list 2>/dev/null | grep -icE 'torch|nvidia|triton' > /dev/null \
        && echo "AVISO: sobrou resíduo de torch/cuda" || echo "OK: cadeia PyTorch removida"

FROM python:3.13-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    VENV_PATH="/opt/pysetup/.venv" \
    PATH="/opt/pysetup/.venv/bin:$PATH"

COPY --from=builder /opt/pysetup /opt/pysetup

WORKDIR /app

COPY src ./src
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini .
COPY entrypoint.sh .
COPY storage ./storage

RUN sed -i 's/\r$//' entrypoint.sh && \
    chmod +x entrypoint.sh && \
    useradd --create-home appuser && \
    mkdir -p storage/xml/zip storage/xml/current storage/openalex/researcher storage/openalex/article logs && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["fastapi", "run", "src/simcc", "--host", "0.0.0.0", "--workers", "4"]
