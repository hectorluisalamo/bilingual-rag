# api/core/db.py
from sqlalchemy import create_engine, text
from api.core.config import settings
import os, glob, logging

log = logging.getLogger("api.db")

engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,         # drops dead connections
    pool_recycle=300,           # avoid stale sockets
)

def run_sql_file(path: str):
    with engine.begin() as conn:
        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            conn.exec_driver_sql(stmt + ";")

def run_startup_migrations():
    # Execute *.sql in migrations/ in lexical order
    paths = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "..", "migrations", "*.sql")))
    # Also support when running from project root inside container
    if not paths and os.path.isdir("migrations"):
        paths = sorted(glob.glob("migrations/*.sql"))
    for p in paths:
        try:
            log.info("migration start %s", p)
            run_sql_file(p)
            log.info("migration ok    %s", p)
        except Exception as e:
            log.warning("migration skip %s (%s)", p, type(e).__name__)
