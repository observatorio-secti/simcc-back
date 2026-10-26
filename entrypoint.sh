#!/bin/sh
set -e

# Run database migrations before starting the API.
alembic upgrade head

# Replace the shell process so container signals reach FastAPI.
if [ -n "$ROOT_PATH" ]; then
    exec fastapi run src/simcc --host 0.0.0.0 --workers 4 --root-path "$ROOT_PATH"
else
    exec fastapi run src/simcc --host 0.0.0.0 --workers 4
fi
