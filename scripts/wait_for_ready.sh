#!/usr/bin/env bash
set -euo pipefail
URL="${1:-http://localhost:8000/health/ready}"
TIMEOUT="${2:-60}"
for i in $(seq 1 "$TIMEOUT"); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || true)
  if [ "$code" = "200" ]; then
    echo "Ready after ${i}s"
    exit 0
  fi
  sleep 1
done
echo "Service not ready after ${TIMEOUT}s"; exit 1
