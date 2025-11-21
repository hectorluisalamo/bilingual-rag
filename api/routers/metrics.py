from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from fastapi import APIRouter

REQUESTS = Counter("rag_requests_total", "Total RAG requests", ["route", "index", "topic", "langs"])
ERRORS   = Counter("rag_errors_total", "Total errors", ["code"])
LATENCY  = Histogram("rag_request_latency_ms", "Request latency (ms)", buckets=[100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000])
DB_LAT   = Histogram("rag_db_latency_ms", "DB query latency (ms)")
EMB_LAT  = Histogram("rag_embed_latency_ms", "Embedding latency (ms)")

router = APIRouter()

@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
