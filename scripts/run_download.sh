#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Configure these ──────────────────────────────────────
FRAME="myframe"                            # frame name from credentials.ini
CONFIG="${SCRIPT_DIR}/../config.ini"       # path to credentials.ini
LOG_FILE="${HOME}/aura-downloads.log"
# ─────────────────────────────────────────────────────────
PYTHON="${SCRIPT_DIR}/../venv/bin/python"
DOWNLOADER="${SCRIPT_DIR}/../download-aura-photos.py"

{
  echo "=== $(date --iso-8601=seconds)  frame=${FRAME} ==="
  "${PYTHON}" "${DOWNLOADER}" --config "${CONFIG}" "${FRAME}"
  echo "=== done (exit $?) ==="
} >> "${LOG_FILE}" 2>&1
