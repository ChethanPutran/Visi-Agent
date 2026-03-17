#!/bin/bash
# scripts/run_api.sh

set -euo pipefail

# --------------------------------------------
# Environment loading
# --------------------------------------------

NODE_ENV="${NODE_ENV:-development}"
ENV_FILE=".env.${NODE_ENV}"

if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    set -a          # automatically export all variables
    source "$ENV_FILE"
    set +a
else
    echo "WARNING: $ENV_FILE not found, using system environment"
fi

# --------------------------------------------
# Required environment variables
# --------------------------------------------

if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "ERROR: GEMINI_API_KEY is not set"
    exit 1
fi

# --------------------------------------------
# Defaults
# --------------------------------------------
: "${APP_HOST:?APP_HOST is required in env}"
: "${APP_PORT:?APP_PORT is required in env}"
: "${API_WORKERS:?API_WORKERS is required in env}"
: "${LOG_LEVEL:?LOG_LEVEL is required in env}"

APP_ENV="${APP_ENV:-$NODE_ENV}"
HOST="$APP_HOST"
# HOST="${APP_HOST:-0.0.0.0}"
PORT="$APP_PORT"
# PORT="${APP_PORT:-8000}"
WORKERS="$API_WORKERS"
# WORKERS="${API_WORKERS:-4}"
LOG_LEVEL="$LOG_LEVEL"
# LOG_LEVEL="${LOG_LEVEL:-info}"
# # --------------------------------------------


# --------------------------------------------
# Startup info
# --------------------------------------------

echo "=================================================="
echo " Starting Video Analytics API"
echo "--------------------------------------------------"
echo " Environment : $APP_ENV"
echo " Host        : $HOST"
echo " Port        : $PORT"
echo " Workers     : $WORKERS"
echo " Log Level   : $LOG_LEVEL"
echo "=================================================="

# --------------------------------------------
# Run API
# --------------------------------------------

if [ "$APP_ENV" = "development" ]; then
    echo "Running in development mode (auto-reload enabled)"
    exec python main.py\
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        --log-level "$LOG_LEVEL"
else
    echo "Running in production mode"
    exec python main.py \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level "$LOG_LEVEL"
fi

# --------------------------------------------