#!/usr/bin/env bash
set -euo pipefail
FILE="$1"
pg_restore --clean --if-exists -d "postgresql://postgres:postgres@localhost:5432/rag" "$FILE"
