from sqlalchemy import text, bindparam
from api.core.db import engine, VECTOR_ADAPTER
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

def _build_sql(use_literal: bool, with_topic: bool, with_country: bool):
    cast = "CAST(:qvec AS vector)" if use_literal else ":qvec"
    filters = ["d.approved = TRUE", "d.lang IN :langs", "c.index_name = :index_name"]
    if with_topic:
        filters.append("d.topic = :topic")
    if with_country:
        filters.append("d.country = :country")
    where = " AND ".join(filters)
    return text(f"""
        SELECT c.text, c.section, c.doc_id, d.source_uri, d.lang, d.published_at,
               1 - (c.embedding <=> {cast}) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.doc_id
        WHERE {where}
        ORDER BY c.embedding <=> {cast}
        LIMIT :k
    """).bindparams(bindparam("langs", expanding=True))
 
def search_similar(query_vec: list, k: int = 8, lang_filter=("en","es"), 
                   topic: str | None = None, country: str | None = None, 
                   index_name: str = "default") -> List[Dict]:
    langs = list(lang_filter)
    with engine.begin() as conn:
        params = {"qvec": query_vec, "langs": langs, "k": k, "topic": topic,
                  "country": country, "index_name": index_name}
        if VECTOR_ADAPTER:
            sql = _build_sql(use_literal=False, with_topic=bool(topic), with_country=bool(country))
            rows = conn.execute(sql, params).mappings().all()
        else:
            sql = _build_sql(use_literal=True, with_topic=bool(topic), with_country=bool(country))
            rows = conn.execute(sql, params).mappings().all()
    return [dict(r) for r in rows]
