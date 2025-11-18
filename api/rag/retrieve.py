from sqlalchemy import text, create_engine
from api.core.config import settings
from typing import List, Dict
from functools import lru_cache

@lru_cache
def get_engine():
    """
    Lazily create the SQLAlchemy engine.
    Returns None when DB_URL is not configured (e.g., unit tests without DB).
    """
    url = settings.db_url
    if not url:
        return None
    return create_engine(url, pool_pre_ping=True)   
 
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
    engine = get_engine()
    if engine is None:
        # Contract-safe: no DB configured → return empty result
        return []
    with engine.begin() as conn:
        rows = conn.execute(sql, {"qvec": query_vec, "k": k, "langs": list(lang_filter)}).mappings().all()
    return [dict(r) for r in rows]
