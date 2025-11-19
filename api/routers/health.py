from fastapi import APIRouter
from sqlalchemy import text
from api.core.db import engine
from api.core.config import settings
import redis

router = APIRouter()

_r = redis.from_url(settings.redis_url) if settings.redis_url else None

@router.get("/live")
def live():
    return {"status": "ok"}

@router.get("/ready")
def ready():
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        if _r:
            _r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "degraded", "error": type(e).__name__}
    
@router.get("/dbdiag")
def dbdiag():
    try:
        with engine.begin() as conn:
            ext = conn.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'")).fetchone()
            docs = conn.execute(text("SELECT count(*) FROM documents")).scalar()
            chks = conn.execute(text("SELECT count(*) FROM chunks")).scalar()
        return {"vector_ext": bool(ext), "documents": int(docs or 0), "chunks": int(chks or 0)}
    except Exception as e:
        return {"error": type(e).__name__, "message": str(e)}

@router.get("/routes")
def routes():
    # lightweight registration check
    return {
        "paths": ["/health/live", "/health/ready", "/health/dbdiag", "/health/routes"]
    }
