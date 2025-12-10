try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    HAVE_PROM = True
except Exception:
    HAVE_PROM = False
    Counter = Histogram = None

from fastapi import APIRouter, Response

router = APIRouter()

# Define metrics
if HAVE_PROM:
    REQUESTS = Counter(
        "rag_requests_total", "Total RAG requests", ["route", "index", "topic", "langs"]
    )
    ERRORS = Counter("rag_errors_total", "Total errors", ("code",))
    LATENCY = Histogram(
        "rag_request_latency_ms",
        "Request latency (ms)",
        buckets=[100,250,500,750,1000,1500,2000,3000,5000],
    )
    EMB_LAT = Histogram(
        "rag_embed_latency_ms", 
        "Embedding latency (ms)"
    )
    DB_LAT  = Histogram(
        "rag_db_latency_ms", 
        "DB latency (ms)"
    )
    
    @router.get("/metrics")
    def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
else:
    REQUESTS = ERRORS = LATENCY = EMB_LAT = DB_LAT = None
    
    @router.get("/metrics")
    def metrics_stub():
        return {"error": "Prometheus client library is not available"}