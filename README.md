# Latino RAG Chatbot :mag:

Bilingual (ES/EN) retrieval-augmented QA with grounded citations. Tuned for Latino culture, civics, health, and education. Production-lite: FastAPI + pgvector + Redis + Streamlit, with metrics and evals.


![Static Badge](https://img.shields.io/badge/License-MIT-blue)
![Static Badge](https://img.shields.io/badge/Built%20with-Python-green)
[![CI](https://github.com/hectorluisalamo/bilingual-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/hectorluisalamo/bilingual-rag/actions/workflows/ci.yml)

## Quickstart
```bash
cp .env.example .env    # add OPENAI_API_KEY
make up              # start db, redis, api, ui
make health          # {"status":"ok", ...}
make seed            # ingest catalog (c300o45); ok and a few fails are fine
open http://localhost:8501
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
            "topic_hint": "food|culture|health|civics|education|null",
            "country_hint": "US|MX|VE|...|null",
            "index_name": "c300o45 (default) | c900 | default"
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