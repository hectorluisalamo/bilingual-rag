# Latino RAG Chatbot :mag:

Bilingual (ES/EN) retrieval-augmented QA with grounded citations. Tuned for Latino culture, civics, health, and education. Production-lite: FastAPI + pgvector + Redis + Streamlit, with metrics and evals.

![Static Badge](https://img.shields.io/badge/License-MIT-blue)
![Static Badge](https://img.shields.io/badge/Built%20with-Python-green)
[![CI](https://github.com/hectorluisalamo/bilingual-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/hectorluisalamo/bilingual-rag/actions/workflows/ci.yml)

Live demo: [<your-url>](https://bilingual-rag.onrender.com/)
Code: [<repo-url>](https://github.com/hectorluisalamo/bilingual-rag)
Metrics (50-item gold set, reranker ON):
- Default index c300o45 → R@1 0.74, R@5 0.80, p95 ≈ 2.03s
- Alternate c900 → R@5 0.84, p50 ≈ 0.57s
What’s different:
- Router (FAQ/BM25) → skips RAG for exact matches
- Layered retrieval (lang/topic filters + cross-encoder re-rank)
- Memory (Redis; TTL 48h) for language prefs & entities
- Freshness/version awareness; citation dates shown
- Eval harness + metrics endpoint

Stack: FastAPI, pgvector, Redis, Streamlit, OpenAI embeddings, HF reranker, Docker Compose, Prometheus.

## Quickstart

### A) Docker Compose (recommended)
```bash
cp .env.example .env    # add OPENAI_API_KEY
make up              # start db, redis, api, ui
make health          # {"status":"ok", ...}
make seed            # uses c300o45 tokens=300 overlap=45; ok if a few fail (422/500)
open http://localhost:8501
```

### B) Local API + Dockerized Postgres (dev only)
```bash
docker run -d --name rag-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=rag -p 5432:5432 pgvector/pgvector:pg16
export DB_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/rag
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Query Examples**
```bash
curl -s -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Qué es una arepa?","k":5,"lang_pref":["es"],"topic_hint":"food"}' | jq

curl -s -X POST http://localhost:8000/query/ \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Cómo solicito un ITIN?","k":5,"lang_pref":["es"],"topic_hint":"civics"}' | jq
```
## API Contract

* **Post /query/**
    * Request:
        ```json
        {
            "query": "string (≤512 chars)",
            "k": 1-8,
            "lang_pref": ["es","en"],
            "use_reranker": true,
            "topic_hint": "food|culture|health|civics|education|null"
        }
        ```
    * Response:
        ```json
        {
            "route": "faq|rag",
            "answer": "string",
            "citations": [{"uri":"...","snippet":"...","date":"...","score":0.73}],
            "request_id": "uuid"
        }
        ```
    * Errors: JSON {code,message,context} (never HTML)


### UI note

The UI runs on a single index (`c300o45`). The index selector is hidden in this build to avoid confusion.

## Index naming
We use `c<chunk_tokens>o<overlap_tokens>`.

- `c300o45` → chunks of **300 tokens** with **45-token overlap**.
Why this default? It maximized **first-hit accuracy (R@1 0.74)** while keeping **R@5 0.80** and p95 ≈ 2.0s on our 50-item bilingual/Spanglish set.


## Retrieval policy (production-lite)

- Router: `faq` short-circuits exact matches; otherwise `rag`.
- Retriever: vector search with `lang/topic` filters → reranker.
- **Fallback:** if filtered search returns 0 hits, service retries once **without `topic`** and with `lang_pref = ["es","en"]`. The UI mirrors this and informs the user.

## Runbook

* **Health:** GET /health/ready → {"status":"ok"}
* **Metrics:** GET /metrics (Prometheus format)
* **Logs:** JSON with request_id, index, k, duration_ms

## Deploy

```bash
make up        # local docker-compose
make logs      # tail containers
make down -v   # stop and wipe volumes
```

## Troubleshooting

- `vector <=> numeric[]` → psycopg2 didn’t bind your list as `vector`. Fix: we register pgvector automatically; if it fails, we fall back to `CAST(:qvec AS vector)`. Ensure you’re on the `pgvector/pgvector:pg16` image.
- `:qvec::vector` syntax error → use `CAST(:qvec AS vector)` (already patched).
- 404 `/health/dbdiag` → router not mounted. Verify `app.include_router(health.router, prefix="/health")`.
- Empty citations? Ensure you seeded the **c300o45** index:
  `make seed`  (uses tokens=300, overlap=45).
- Check counts:
  ```sql
  SELECT d.topic, COUNT(*) FROM chunks c JOIN documents d ON d.id=c.doc_id
  WHERE c.index_name='c300o45' GROUP BY 1 ORDER BY 1;

## Repo Layout

api/           FastAPI app
scripts/       ingest & eval tools
ui/            Streamlit demo
migrations/    SQL schema (pgvector)
data/          catalog & gold set
tests/         contract + eval smoke tests
docs/          architecture, runbook, case study

## Metrics

| **Variant**  | **Chunk** | **Overlap** | **Embed** | **R@1** | **R@3** | **R@5** | **p50 ms** | **p95 ms** | **Notes** |
|------------- |----------:|------------:|-----------|--------:|--------:|--------:|-----------:|-----------:|-----------|
| default      | 600       | 60          | e3-small  | 0.52    | 0.70    | 0.76    | 1324       | 2280       | Baseline  |
| **c300o45**  | 300       | 45          | e3-small  | **0.74**| 0.80    | 0.80    | 1332       | 2030       | **Default (production-lite)** |
| c300         | 300       | 30          | e3-small  | 0.66    | 0.74    | 0.74    | 1345       | 1583       | Better R@1 than baseline |
| c900         | 900       | 90          | e3-small  | 0.38    | 0.66    | **0.84**| **568**    | 1537       | Deeper recall; faster p50 |

## License

MIT (code). Respect publishers’ ToS; we store URLs + snippets only.

## Contributing

Pull requests and discussions are welcome.

Created and maintained by **Hector Luis Alamo**.

📫 [LinkedIn](https://www.linkedin.com/in/hector-luis-alamo-90432941/)