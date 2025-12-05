from sqlalchemy import text
from api.core.db import engine
from typing import List, Dict
import re

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
 
def search_similar(
    query_vec: list, 
    k: int = 8, 
    lang_filter: tuple[str, ...] = ("en","es"),
    topic: str | None = None, 
    country: str | None = None, 
    index_name: str = "default"
):
    sql = text("""
        SELECT
          c.text,
          c.section,
          c.doc_id,
          d.source_uri,
          d.lang,
          d.topic,
          d.country,
          d.published_at,
          1 - (c.embedding <=> :qvec) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.doc_id
        WHERE d.approved = TRUE
          AND c.embedding IS NOT NULL
          AND d.lang = ANY(:langs)
          AND (:topic IS NULL OR d.topic = :topic)
          AND (:country IS NULL OR d.country = :country)
          AND (:index_name IS NULL OR c.index_name = :index_name)
        ORDER BY c.embedding <=> :qvec
        LIMIT :k
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "qvec": query_vec,                 
                "langs": list(lang_filter or ()),
                "topic": topic,
                "country": country,
                "index_name": index_name,
                "k": int(k),
            },
        ).mappings().all()

    # Light, deterministic boost if query token appears in URI or text
    def _tok(s): 
        import re
        return set(re.findall(r"\w+", (s or "").lower()))
    qtok = _tok(getattr(search_similar, "_last_q", ""))  # Set by caller
    def bonus(r):
        uri = (r.get("source_uri") or "").lower()
        txt = (r.get("text") or "").lower()
        b = 0
        for t in qtok:
            if t and t in uri: b += 2
            if t and t in txt: b += 1
        return (b, float(r.get("score") or 0.0))

    return sorted(rows, key=bonus, reverse=True)
