#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
pg_dump "postgresql://postgres:postgres@localhost:5432/rag" -Fc -f "backup_rag_${TS}.dump"
echo "Wrote backup_rag_${TS}.dump"
