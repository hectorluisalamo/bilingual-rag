# RAG Service Runbook

## Dashboards
- Prometheus: scrape `/metrics` on port 8000.

## Oncall Checks
- `/health/ready` returns `{"status":"ok"}`.
- Error rate < 2% (rag_errors_total / rag_requests_total).
- p95 latency < 1800ms (rag_request_latency_ms).

## Common Incidents
- Embedding API 429: spikes `EMB_LAT`, increase backoff or switch to fallback.
- DB slow: `DB_LAT` > 500ms; rebuild IVF index (scripts/db_maint.sql) or check connection saturation.

## Rollback
- Set `DEFAULT_INDEX_NAME` to last known good.
- If data regression: restore the latest dump via `scripts/db_restore.sh`.
