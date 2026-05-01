#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <images-dir>" >&2
  exit 1
fi

DIR="$1"

if [ ! -d "$DIR" ]; then
  echo "Not a directory: $DIR" >&2
  exit 1
fi

count=0
for f in "$DIR"/*.url; do
  [ -e "$f" ] || continue
  mv "$f" "${f%.url}.mp4"
  count=$((count + 1))
done

echo "Renamed $count file(s)"
