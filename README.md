# Latino RAG Chatbot

## Quickstart
1. `cp .env.example .env` and fill keys
2. `docker compose up --build`
3. Health: `GET http://localhost:8000/health/live`
4. Ingest a URL: `POST /ingest/url`
5. Ask: `POST /query`

### Design (MVP)
Router (FAQ/BM25) → Retriever (pgvector + metadata) → Re-ranker (optional) → Generator (LLM) → Guardrails