#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

VERSION="${1:-v1.1.0}"
OUT_DIR="release"
ARCHIVE_NAME="face-aging-simulator-${VERSION}.zip"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR" uploads outputs

zip -r "$OUT_DIR/$ARCHIVE_NAME" \
  frontend backend ai uploads outputs Dockerfile docker-compose.yml render.yaml README.md \
  -x "*/node_modules/*" "*/.venv/*" "*/__pycache__/*" "*.pyc" "outputs/*.zip"

echo "Release archive generated: $OUT_DIR/$ARCHIVE_NAME"
