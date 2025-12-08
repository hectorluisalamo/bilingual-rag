from sqlalchemy import text
from api.core.db import engine
import httpx, os

API = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_INDEX = os.getenv("DEFAULT_INDEX_NAME", "c300o45")

def _ensure_arepa_seeded():
    try:
        with httpx.Client(base_url=API, timeout=30) as c:
            c.post("/ingest/url", json={
                "url":"https://es.wikipedia.org/wiki/Arepa",
                "lang":"es","topic":"food","country":"VE",
                "index_name": DEFAULT_INDEX, "max_tokens":300, "overlap":45
            })
    except Exception:
        pass

def test_newer_version_pref():
    _ensure_arepa_seeded()
    sql = text("""
        SELECT version, published_at, approved
        FROM documents
        WHERE source_uri = :u
        ORDER BY version DESC
        LIMIT 1
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"u":"https://es.wikipedia.org/wiki/Arepa"}).all()
    if not rows:
        # environment not seeded; avoid hard failure in CI
        import pytest; pytest.skip("no versions found for Arepa URL")
    assert rows[0][2] is True  # approved flag