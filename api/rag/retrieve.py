from api.core.config import settings
from sqlalchemy import create_engine, text
from typing import List, Dict

engine = create_engine(settings.db_url, pool_pre_ping=True)

def search_similar(query_vec: list, k: int=8, lang_filter=("en", "es")) -> List[Dict]:
    sql = text("""
        SELECT c.text, c.section, c.doc_id, d.source_uri, d.lang, d.published_at,
               1 - (c.embedding <=> :qvec) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.doc_id
        WHERE d.approved = TRUE AND d.lang = ANY(:langs)
        ORDER BY c.embedding <=> :qvec
        LIMIT :k
    """)
    with engine.begin() as conn:
        rows = conn.execute(sql, {"qvec": query_vec, "k": k, "langs": list(lang_filter)}).mappings().all()
    return [dict(r) for r in rows]
