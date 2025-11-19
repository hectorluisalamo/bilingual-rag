#!/usr/bin/env bash
set -euo pipefail
API=${API:-http://localhost:8000}
cat data/docs_catalog.json | jq -c '.[]' | while read -r row; do
  URL=$(echo "$row" | jq -r .url)
  LANG=$(echo "$row" | jq -r .lang)
  TOPIC=$(echo "$row" | jq -r .topic)
  COUNTRY=$(echo "$row" | jq -r .country)
  curl -s -X POST "$API/ingest/url" -H "Content-Type: application/json" \
    -d "{\"url\":\"$URL\",\"lang\":\"$LANG\",\"topic\":\"$TOPIC\",\"country\":\"$COUNTRY\"}" >/dev/null || true
done
echo "Ingest attempted for all catalog URLs."
