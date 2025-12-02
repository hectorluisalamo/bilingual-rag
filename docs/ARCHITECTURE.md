flowchart LR
    UI[Streamlit UI] -->|HTTP| API[/FastAPI /query/ (validate, normalize, metrics)/]
    API --> ROUTER[Router: FAQ/BM25]
    ROUTER -->|faq| RESP[Return FAQ answer]
    ROUTER -->|rag| EMB[Embed query (OpenAI e3-small)]
    EMB --> VEC[Vector search (pgvector)\nfilters: lang/topic/country/index]
    VEC --> RERANK[Cross-encoder re-rank Top-K]
    RERANK --> MEM[(Redis memory\nprefs/entities, TTL)]
    MEM --> GEN[Generator w/ per-claim citations\n+ guardrails]
    GEN --> RESP[JSON: {route, answer, citations[], request_id}]
    subgraph Storage
      PG[(Postgres + pgvector\nchunks: vector(1536))]
    end
    VEC --- PG
    subgraph Ingest
      ING[URLs/PDFs → clean → sentence+token chunk → embed → store\nmetadata: lang, topic, country, version, index_name]
      ING --> PG
    end
    API --> METRICS[/Prometheus /metrics, JSON logs/]
