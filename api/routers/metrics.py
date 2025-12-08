from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

# Define metrics
REQUESTS = Counter(
    "rag_requests_total", "Total RAG requests", ["route", "index", "topic", "langs"]
)
ERRORS = Counter("rag_errors_total", "Total errors", ["code"])
LATENCY = Histogram(
    "rag_request_latency_ms",
    "Request latency (ms)",
    buckets=[100,250,500,750,1000,1500,2000,3000,5000],
)
EMB_LAT = Histogram(
    "rag_embed_latency_seconds", 
    "Embedding latency", 
    buckets=(0.05,0.1,0.2,0.5,1)
)
DB_LAT  = Histogram(
    "rag_db_latency_seconds", 
    "DB latency", 
    buckets=(0.01,0.05,0.1,0.2,0.5,1)
)

router = APIRouter()

@router.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
