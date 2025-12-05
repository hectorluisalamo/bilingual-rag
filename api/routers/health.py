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
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except Exception:
        db = "degraded"
    return {"status": "ok", "db": db}
    
@router.get("/dbdiag")
def dbdiag():
    try:
        out = {}
        with engine.connect() as conn:
            ver = conn.execute(text("select version()")).scalar()
            db  = conn.execute(text("select current_database()")).scalar()
            user= conn.execute(text("select current_user")).scalar()
            exts = [r[0] for r in conn.execute(text("select extname from pg_extension order by 1"))]
            # Counts guarded
            try:
                dc = conn.execute(text("select count(*) from documents")).scalar()
                cc = conn.execute(text("select count(*) from chunks")).scalar()
            except Exception:
                dc = cc = None
        out.update({
            "version": ver, "database": db, "user": user,
            "extensions": exts, "documents": dc, "chunks": cc
        })
        return out
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

@router.get("/health/ready")
def ready():
    # cheap DB ping; don't crash on failure
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db = "ok"
    except Exception:
        db = "degraded"
    return {"status": "ok", "db": db}