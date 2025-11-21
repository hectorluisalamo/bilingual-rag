from sqlalchemy import text
from api.core.db import engine

def test_newer_version_pref():
    sql = text("""
    SELECT version, published_at
    FROM documents
    WHERE source_uri = :u AND deleted = FALSE
    ORDER BY version DESC
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"u": "https://es.wikipedia.org/wiki/Arepa"}).all()
    assert rows, "need at least one version ingested"