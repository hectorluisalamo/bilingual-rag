# api/core/db.py
from sqlalchemy import create_engine
import os, glob, logging

log = logging.getLogger("api.db")

DB = os.getenv("DB_URL", "")

engine = create_engine(
    DB,
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
