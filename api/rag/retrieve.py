import re
from sqlalchemy import text, bindparam
from api.core.db import engine
from typing import List, Dict, Iterable, Optional
from sqlalchemy.dialects.postgresql import TEXT
from pgvector.sqlalchemy import Vector

_WORD = re.compile(r"\w+", re.UNICODE)

def _to_pgvector_literal(vec) -> str:
    if isinstance(vec, str) and vec.strip().startswith("["):
        return vec.strip()
    # cast all items to float, ignoring non-numerics
    nums = [float(x) for x in vec]
    return "[" + ",".join(f"{x:.6f}" for x in nums) + "]"

def _norm(s: str) -> str:
    # lowercase, strip accents-ish by NFKD ASCII fallback
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower()

def entity_from_query(q: str) -> str | None:
    # take the longest alphabetic token (very simple entity guess)
    toks = [t for t in _WORD.findall(q) if t.isalpha()]
    return max(toks, key=len).lower() if toks else None

def prefer_entity(rows: List[Dict], q: str) -> List[Dict]:
    ent = entity_from_query(q)
    if not ent:
        return rows
    ent = _norm(ent)
    scored = []
    for r in rows:
        uri = _norm(r.get("source_uri", ""))
        txt = _norm(r.get("text", ""))
        bonus = 0
        if f"/{ent}" in uri:
            bonus += 0.4
        if f"{ent} " in txt or f" {ent}" in txt:
            bonus += 0.2
        scored.append(( (r.get("score") or 0) + bonus, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored]

def dedup_by_uri(rows):
    seen = set()
    deduped = []
    for r in rows:
        uri = r["source_uri"]
        if uri in seen:
            continue
        seen.add(uri)
        deduped.append(r)
    return deduped

SQL_TXT = """
SELECT
  c.text,
  c.section,
  c.doc_id,
  d.source_uri,
  d.lang,
  d.published_at,
  1 - (c.embedding <=> :qvec) AS score
FROM chunks c
JOIN documents d ON d.id = c.doc_id
WHERE d.approved = TRUE
  AND c.index_name = :index_name
  AND d.lang IN :langs
  -- optional topic/country gates, only apply if provided
  /*topic*/    /*country*/
ORDER BY c.embedding <=> :qvec
LIMIT :k
"""

def _apply_optional_filters(sql: text, topic: Optional[str] = None, country: Optional[str] = None) -> str:
    s = SQL_TXT
    if topic:
        s = s.replace("/*topic*/", "AND d.topic = :topic")
    else:
        s = s.replace("/*topic*/", "")
    if country:
        s = s.replace("/*country*/", "AND d.country = :country")
    else:
        s = s.replace("/*country*/", "")
    return s

def search_similar(
    query_vec: list[float],
    *,
    k: int,
    lang_filter: Iterable[str],
    index_name: str,
    topic: Optional[str] = None,
    country: Optional[str] = None,
) -> list[dict]:
    langs = list(lang_filter) or ["es", "en"]

    sql = text(_apply_optional_filters(SQL_TXT, topic, country)).bindparams(
        bindparam("qvec", type_=Vector(1536)),
        bindparam("langs", value=langs, expanding=True),
        bindparam("index_name", type_=TEXT),
        bindparam("k"),
    )
    if topic:
        sql = sql.bindparams(bindparam("topic", type_=TEXT))
    if country:
        sql = sql.bindparams(bindparam("country", type_=TEXT))

    with engine.connect() as conn: 
        rows = conn.execute(
            sql,
            {
                "qvec": query_vec, 
                "index_name": index_name, 
                "k": int(k)}
                **({"topic": topic} if topic else {}),
                **({"country": country} if country else {})
        ).mappings().all()
        return [dict(r) for r in rows]
