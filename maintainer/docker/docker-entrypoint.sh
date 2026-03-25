#!/bin/sh
set -eu

SETTINGS_FILE="${SEARCHARR_SETTINGS_FILE:-/app/settings.py}"

mkdir -p /app/data

echo "========================================"
echo "  Searcharr-nxg Container"
echo "  Version: ${PROJECT_VERSION:-dev-local}"
echo "  Build: ${PROJECT_BUILD_NUMBER:-local}"
echo "  Settings: ${SETTINGS_FILE}"
echo "========================================"

if [ ! -f "$SETTINGS_FILE" ]; then
  echo "WARNING: settings file does not exist yet: ${SETTINGS_FILE}"
fi

if [ "$#" -eq 0 ]; then
  exec searcharr-nxg
fi

exec searcharr-nxg "$@"
