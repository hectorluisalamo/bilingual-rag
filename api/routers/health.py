from fastapi import APIRouter
from sqlalchemy import text
from api.core.db import engine
from api.core.config import settings
import os, httpx, redis, time

router = APIRouter()

_rds = redis.from_url(settings.redis_url) if settings.redis_url else None

@router.get("/live")
def live():
    return {"status": "ok"}

@router.get("/ready")
def ready():
    try:
        t0 = time.time()
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        d_ms = int((time.time() - t0) * 1000)
        if _rds:
            _rds.ping()
        return {"status": "ok", "d_ms": d_ms, "embeddings": "openai" if settings.openai_api_key else "fallback"}
    except Exception as e:
        return {"status": "degraded", "error": type(e).__name__}
    
@router.get("/dbdiag")
def dbdiag():
    try:
        with engine.begin() as conn:
            ext = conn.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'")).fetchone()
            docs = conn.execute(text("SELECT count(*) FROM documents")).scalar()
            chks = conn.execute(text("SELECT count(*) FROM chunks")).scalar()
            idxs = conn.execute(text("SELECT index_name, count(*) FROM chunks GROUP BY index_name ORDER BY index_name")).all()
        return {"vector_ext": bool(ext), "documents": int(docs or 0), "chunks": int(chks or 0),
                "indices": [{"index_name": r[0], "chunks": int(r[1])} for r in idxs]}
    except Exception as e:
        return {"error": type(e).__name__, "message": str(e)}

@router.get("/routes")
def routes():
    # lightweight registration check
    return {
        "paths": ["/health/live", "/health/ready", "/health/dbdiag", "/health/routes"]
    }

@router.get("/embeddings")
async def embeddings_probe():
    base = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
    key  = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    if not key:
        return {"ok": False, "reason": "no_api_key"}
    payload = {"input": "hola", "model": model}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{base}/embeddings", headers={"Authorization": f"Bearer {key}"}, json=payload)
        return {"ok": r.status_code == 200, "status": r.status_code, "model": model, "base": base,
                "body": r.json() if r.headers.get("content-type","").startswith("application/json") else r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
    
@router.get("/env")
def env():
    return {"db_url": settings.db_url, "default_index_name": settings.default_index_name}

@router.get("/net")
def net(url: str = "https://es.wikipedia.org/wiki/Arepa"):
    t0 = time.time()
    try:
        r = httpx.get(url, timeout=5.0)
        ms = int((time.time() - t0) * 1000)
        return {"ok": True, "status": r.status_code, "ms": ms}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}
    
@router.get("/emb")
async def emb_probe(q: str = "hola"):
    from api.rag.embed import embed_texts
    vecs = await embed_texts([q])
    return {
        "ok": bool(vecs and isinstance(vecs, list) and vecs[0] is not None), 
        "dim": len(vecs[0]) if vecs and vecs[0] is not None else 0
    }
