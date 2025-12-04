import os
from typing import Any

METRICS_ENABLED = os.getenv("METRICS_ENABLED", "0") in ("1", "true", "True")

try:
    if METRICS_ENABLED:
        from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    else:
        raise ImportError("metrics disabled")
except Exception:
    # Lightweight shims so rest of app doesn't break
    class _Noop:
        def labels(self, *a: Any, **kw: Any):
            return self
        def observe(self, *a: Any, **kw: Any):
            return None
        def inc(self, *a: Any, **kw: Any):
            return None
        def time(self): 
            class _Ctx: 
                def __enter__(self):
                    pass
                def __exit__(self, *exc):
                    pass
            return _Ctx()

    Counter = Histogram = _Noop
    def generate_latest():
        return b""
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

# Define metrics
REQUESTS = Counter("rag_requests_total", "Total requests",) if METRICS_ENABLED else _Noop()
LATENCY = Histogram("rag_request_latency_seconds", "Request latency", buckets=(0.1,0.3,0.5,1,2,5)) if METRICS_ENABLED else _Noop()
EMB_LAT = Histogram("rag_embed_latency_seconds", "Embedding latency", buckets=(0.05,0.1,0.2,0.5,1)) if METRICS_ENABLED else _Noop()
DB_LAT  = Histogram("rag_db_latency_seconds", "DB latency", buckets=(0.01,0.05,0.1,0.2,0.5,1)) if METRICS_ENABLED else _Noop()

# FastAPI route
from fastapi import APIRouter, Response
router = APIRouter()
@router.get("/metrics")
def metrics():
    if not METRICS_ENABLED:
        return Response(content="# metrics disabled\n", media_type="text/plain")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
