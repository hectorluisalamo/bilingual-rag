from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from api.core.db import engine, VECTOR_ADAPTER
from api.rag.chunk import chunk_by_tokens, split_unicode
from api.rag.embed import embed_texts
from api.rag.fetch import fetch_text
from api.rag.store import upsert_document, insert_chunks
from api.rag.retrieve import _to_pgvector_literal
from bs4 import BeautifulSoup
from sqlalchemy import text as sqltext
import httpx

router = APIRouter()

ALLOWED_DOMAINS = {
    "es.wikipedia.org","www.cdc.gov","www.usa.gov","www.irs.gov",
    "www.uscis.gov","www.vote.gov","www.who.int"
}

class IngestURL(BaseModel):
    url: str
    lang: str = "es"
    topic: str | None = None
    country: str | None = None
    section: str | None = None
    index_name: str = "default"
    max_tokens: int = 600
    overlap: int = 60
    embedding_model: str | None = None

class IngestRaw(BaseModel):
    source_uri: str
    text: str               
    lang: str = "es"
    topic: Optional[str] = None
    country: Optional[str] = None
    section: Optional[str] = None
    index_name: str = "default"
    max_tokens: int = 600
    overlap: int = 60
    embedding_model: Optional[str] = None
    
class PurgeIn(BaseModel):
    url: str


@router.post("/url")
async def ingest_url(item: IngestURL):
    fetched = await fetch_text(item.url)
    text = BeautifulSoup(fetched, "html.parser").get_text(" ")
    sentences = split_unicode(text)
    chunks = [ct for ct in chunk_by_tokens(sentences, max_tokens=item.max_tokens, overlap=item.overlap) if ct[1] > 0]
    if not chunks:
        raise HTTPException(status_code=422, detail="no_chunks_made")

    embeds = await embed_texts([c for c,_ in chunks], model=item.embedding_model)

    # If adapter is not active, cast embeddings to vector literal for insert
    payload = []
    if VECTOR_ADAPTER:
        payload = [(c, t, e, item.section) for (c,t), e in zip(chunks, embeds)]
    else:
        payload = [(c, t, _to_pgvector_literal(e), item.section) for (c,t), e in zip(chunks, embeds)]

    # store
    from sqlalchemy import text
    with engine.begin() as conn:
        doc_id = upsert_document(
            conn, item.url, "url", item.lang,
            item.country, item.topic,
            index_name=item.index_name
        )
        payload = [(c, t, e, item.section) for (c, t), e in zip(chunks, embeds)]
        insert_chunks(conn, doc_id, payload, index_name=item.index_name)
    
    return {
        "doc_id": str(doc_id), 
        "chunks": len(chunks),
        "index_name": item.index_name,
        "max_tokens": item.max_tokens,
        "overlap": item.overlap,
        "embedding_model": item.embedding_model or "default"
    }

@router.post("/purge")
def purge(p: PurgeIn):
    with engine.begin() as conn:
        row = conn.execute(sqltext("SELECT id FROM documents WHERE source_uri=:u"), {"u": p.url}).fetchone()
        if not row:
            return {"deleted": 0}
        conn.execute(sqltext("DELETE FROM documents WHERE id=:i"), {"i": row[0]})
        return {"deleted": 1}
    
@router.get("/_fetch_debug")
async def fetch_debug(url: str):
    got = await fetch_text(url)
    if isinstance(got, httpx.Response):
        return {"kind": "response", "status": got.status_code, "ctype": got.headers.get("content-type")}
    return {"kind": "str", "length": len(str(got))}

@router.post("/raw")
async def ingest_raw(item: IngestRaw):
    txt = (item.text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="empty_text")

    sentences = split_unicode(txt)
    chunks = [ct for ct in chunk_by_tokens(sentences, max_tokens=item.max_tokens, overlap=item.overlap) if ct[1] > 0]
    if not chunks:
        raise HTTPException(status_code=422, detail="no_chunks_made")

    embeds = await embed_texts([c for c,_ in chunks], model=item.embedding_model)
    payload = (
        [(c, t, e, item.section) for (c,t), e in zip(chunks, embeds)]
        if VECTOR_ADAPTER else
        [(c, t, _to_pgvector_literal(e), item.section) for (c,t), e in zip(chunks, embeds)]
    )

    with engine.begin() as conn:
        doc_id = upsert_document(conn, item.source_uri, "raw", item.lang, item.country, item.topic, index_name=item.index_name)
        insert_chunks(conn, doc_id, payload, index_name=item.index_name)

    return {"doc_id": str(doc_id), "chunks": len(chunks), "index_name": item.index_name}
