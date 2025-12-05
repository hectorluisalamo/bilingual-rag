# api/core/db.py
from sqlalchemy import create_engine
import os, glob, logging, re

log = logging.getLogger("api.db")

def _normalize_sqlalchemy_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url  # assume already has +psycopg2 or other driver

def coalesce_db_url() -> str:
    for key in ("DB_URL", "DATABASE_URL", "POSTGRES_URL", "PG_CONNECTION_STRING"):
        val = os.getenv(key, "").strip()
        if val:
            return _normalize_sqlalchemy_url(val)
    return ""

def _mask(url: str) -> str:
    # hide password between ':' and '@'
    return re.sub(r":[^@]+@", ":***@", url or "")

db_url = coalesce_db_url()

if not db_url:
    raise RuntimeError(
        "No DB URL found. Set DATABASE_URL in the service env. "
        "On Render, use Environment → From Database to inject DATABASE_URL."
    )

log.info("DB connecting to %s", _mask(db_url))
engine = create_engine(
    db_url,
    pool_pre_ping=True,         # drops dead connections
    pool_recycle=300,           # avoid stale sockets
    pool_size=int(os.getenv("DB_POOL_SIZE") or 5),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW") or 5),
    future=True,
)

def run_sql_file(path: str):
    with engine.begin() as conn:
        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            conn.exec_driver_sql(stmt + ";")

def run_startup_migrations():
    paths = sorted(glob.glob("migrations/*.sql"))
    for p in paths:
        try:
            log.info(f"migration start {p}")
            run_sql_file(p)
            log.info(f"migration ok {p}")
        except Exception as e:
            log.warning("migration_skip", extra={"msg": f"{p} {type(e).__name__}: {e}"})
