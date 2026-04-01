#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${BASE_DIR}/../../.." && pwd)"
LOG_DIR="${ROOT_DIR}/addons/docs/logs"
mkdir -p "${LOG_DIR}"

STAMP="$(date '+%Y%m%d_%H%M%S')"
LOG_FILE="${LOG_DIR}/helpdesk_smoke_${STAMP}.log"

{
  echo "[INFO] $(date -Iseconds) Starting helpdesk functional smoke run"
  docker exec -i odoo17-docker-community-web-1 \
    python3 /mnt/extra-addons/docs/scripts/helpdesk_functional_smoke_test.py \
    --db ksv17-dev \
    --api-token ksv17-demo-api-token
  echo "[INFO] $(date -Iseconds) Smoke run completed"
} | tee "${LOG_FILE}"
