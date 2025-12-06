# TROUBLESHOOTING

### “operator does not exist: vector <=> numeric[]”
- Cause: embeddings bound as `numeric[]`, not pgvector.
- Fix: ensure `pgvector/pgvector:pg16` image; adapter is registered at connect; code falls back to `CAST(:qvec AS vector)`.

### “syntax error at or near :qvec::vector”
- Cause: Psycopg param parsing.
- Fix: use `CAST(:qvec AS vector)` (already implemented).

### 404 `/health/dbdiag`
- Cause: router not mounted.
- Fix: `app.include_router(health.router, prefix="/health")` in `api/main.py`.

### 500 on `/query` with local API
- Cause: `DB_URL` points at `@db`.
- Fix: `DB_URL=...@localhost:5432/rag` for local; `@db` inside compose.

### Empty results in UI
- Causes: empty index, strict `topic_hint`, `lang_pref=["es"]` but only EN docs.
- Quick fix: unfiltered query; then seed minimal corpus; then check counts SQL.
