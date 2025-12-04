import uuid
from sqlalchemy import text
from api.core.db import engine

URL = "https://es.wikipedia.org/wiki/Arepa"

def test_newer_version_pref():
    seed_sql = text("""
        DELETE FROM documents WHERE source_uri = :u;
        INSERT INTO documents (
            id, source_uri, source_type,  -- <— add source_type
            lang, index_name, version,
            approved, deleted, published_at
        ) VALUES
          (:id1, :u, 'web',  -- <— set a value (e.g., 'web')
           'es', 'c300o45', 1,
           TRUE, FALSE, '2023-01-01'::timestamptz),
          (:id2, :u, 'web',
           'es', 'c300o45', 2,
           TRUE, FALSE, '2024-01-01'::timestamptz);
    """)
    with engine.begin() as conn:
        conn.execute(
            seed_sql,
            {"u": URL, "id1": str(uuid.uuid4()), "id2": str(uuid.uuid4())}
        )

    sql = text("""
        SELECT version, published_at
        FROM documents
        WHERE source_uri = :u AND deleted = FALSE
        ORDER BY version DESC
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"u": URL}).all()

    assert rows, "need at least one version ingested"
    assert rows[0][0] == 2, f"expected newest version first, got {rows[0]}"