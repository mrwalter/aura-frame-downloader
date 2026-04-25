#!/bin/bash
set -euo pipefail

# ── Configure these ──────────────────────────────────────
FRAME="myframe"                    # frame name from credentials.ini
CONFIG="${SCRIPT_DIR}/../config.ini"       # path to credentials.ini
LOG_FILE="${HOME}/aura-downloads.log"
# ─────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${SCRIPT_DIR}/../venv/bin/python"
DOWNLOADER="${SCRIPT_DIR}/../download-aura-photos.py"

{
  echo "=== $(date --iso-8601=seconds)  frame=${FRAME} ==="
  "${PYTHON}" "${DOWNLOADER}" --config "${CONFIG}" "${FRAME}"
  echo "=== done (exit $?) ==="
} >> "${LOG_FILE}" 2>&1
