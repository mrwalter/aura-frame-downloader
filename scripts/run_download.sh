#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Configure these ──────────────────────────────────────
FRAME="myframe"                            # frame name from credentials.ini
CONFIG="${SCRIPT_DIR}/../config.ini"       # path to credentials.ini
IMAGES_DIR="${SCRIPT_DIR}/../images"       # directory where photos/videos are saved
LOG_FILE="${SCRIPT_DIR}/../logs/aura-downloads.log"
# ─────────────────────────────────────────────────────────
mkdir -p "${SCRIPT_DIR}/../logs"
PYTHON="${SCRIPT_DIR}/../venv/bin/python"
DOWNLOADER="${SCRIPT_DIR}/../download-aura-photos.py"
RENAMER="${SCRIPT_DIR}/rename_url_to_mp4.sh"

{
  echo "=== $(date --iso-8601=seconds)  frame=${FRAME} ==="
  "${PYTHON}" "${DOWNLOADER}" --config "${CONFIG}" "${FRAME}" 2>&1 | grep -v ", already downloaded$"
  "${RENAMER}" "${IMAGES_DIR}"
  echo "=== done (exit $?) ==="
} >> "${LOG_FILE}" 2>&1
