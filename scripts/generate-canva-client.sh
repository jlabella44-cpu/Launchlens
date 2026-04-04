#!/bin/bash
set -euo pipefail

SPEC_URL="https://www.canva.dev/sources/connect/api/latest/api.yml"
OUTPUT_DIR="src/listingjet/providers/canva_generated"

echo "Generating Python client from Canva Connect API spec..."

# Prefer openapi-python-client (Python-native, no Java required).
# Falls back to npx @openapitools/openapi-generator-cli if Java 11+ is available.
if command -v openapi-python-client &>/dev/null; then
  echo "Using openapi-python-client..."
  openapi-python-client generate \
    --url "$SPEC_URL" \
    --output-path "$OUTPUT_DIR" \
    --overwrite
else
  JAVA_VER=$(java -version 2>&1 | awk -F '"' '/version/{print $2}' | cut -d. -f1)
  if [ "${JAVA_VER:-0}" -ge 11 ] 2>/dev/null; then
    TEMP_SPEC="/tmp/canva-openapi-spec.yml"
    echo "Using openapi-generator-cli (Java $JAVA_VER)..."
    curl -sL "$SPEC_URL" -o "$TEMP_SPEC"
    npx @openapitools/openapi-generator-cli generate \
      -i "$TEMP_SPEC" \
      -g python \
      -o "$OUTPUT_DIR" \
      --additional-properties=packageName=canva_client,asyncio=true,library=asyncio \
      --global-property=models,apis,supportingFiles
    rm -f "$TEMP_SPEC"
  else
    echo "ERROR: Neither openapi-python-client nor Java 11+ found."
    echo "Install with: pip install openapi-python-client"
    exit 1
  fi
fi

echo "Done! Generated client in $OUTPUT_DIR"
