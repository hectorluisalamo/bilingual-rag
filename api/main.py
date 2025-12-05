from contextlib import asynccontextmanager
from api.core.logging import configure_logging
from api.core.db import engine, run_startup_migrations
from fastapi import FastAPI
from sqlalchemy import text
from api.core.db import coalesce_db_url
from api.core.errors import json_error, EnforceJSONMiddleware
from api.routers import ingest, query, health, metrics, debug


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_startup_migrations()
    yield

db_url = coalesce_db_url()
configure_logging(db_url)

app = FastAPI(lifespan=lifespan)

app.add_middleware(EnforceJSONMiddleware)
app.add_exception_handler(Exception, json_error)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(debug.router, prefix="/debug", tags=["debug"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])

@app.get("/health/dbdiag")
def dbdiag():
    with engine.connect() as conn:
        ver = conn.execute(text("select version()")).scalar_one()
        db  = conn.execute(text("select current_database()")).scalar_one()
        user= conn.execute(text("select current_user")).scalar_one()
        exts= [r[0] for r in conn.execute(text("select extname from pg_extension order by 1"))]
        try:
            dc = conn.execute(text("select count(*) from documents")).scalar_one()
            cc = conn.execute(text("select count(*) from chunks")).scalar_one()
        except Exception:
            dc = cc = None
    return {"version": ver, "database": db, "user": user, "extensions": exts, "documents": dc, "chunks": cc}

@app.get("/debug/sql")
def debug_sql():
    out = {}
    try:
        with engine.begin() as conn:
            out["ping"] = conn.execute(text("select 1")).scalar_one()
            out["ssl"]  = conn.execute(text("show ssl")).scalar_one_or_none()
            out["search_path"] = conn.execute(text("show search_path")).scalar_one()
            out["ext_vector"] = conn.execute(text("select 1 from pg_extension where extname='vector'")).first() is not None
            # Try a tiny vector op only if chunks exists
            try:
                conn.execute(text("select count(*) from chunks")).scalar_one()
                out["chunks_ok"] = True
            except Exception as e:
                out["chunks_ok"] = f"err:{type(e).__name__}"
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out