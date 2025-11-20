from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.core.db import engine
from api.rag.chunk import chunk_by_tokens, extract_html, split_unicode, clean_whitespace
from api.rag.embed import embed_texts
from api.rag.fetch import fetch_text
from api.rag.store import upsert_document, insert_chunks
from bs4 import BeautifulSoup
from io import BytesIO
from pdfminer.high_level import extract_text as pdf_extract
from sqlalchemy import text as sqltext
import httpx

router = APIRouter()

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
    allow_fallback_chunk: bool = True

class IngestPDF(BaseModel):
    path: str
    lang: str = "es"
    topic: str | None = None
    country: str | None = None
    section: str | None = None
    index_name: str = "default"
    max_tokens: int = 600
    overlap: int = 60
    embedding_model: str | None = None
    
class PurgeIn(BaseModel):
    url: str
    

@router.post("/url")
async def ingest_url(item: IngestURL):
    r = await fetch_text(item.url)
    ctype = (r.headers.get("content-type") or "").lower()
    
    try:
        if "application/pdf" in ctype or item.url.lower().endswith(".pdf"):
            # PDF path
            buf = BytesIO(r.content)
            try:
                text = pdf_extract(buf) or ""
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"pdf_extract_failed:{type(e).__name__}")
            text = clean_whitespace(text)
        else:
            # HTML path
            html = r.text if isinstance(r, httpx.Response) else str(r)
            text = extract_html(html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"extract_failed:{type(e).__name__}")
    
    if not text or len(text) < 200:
        if not item.allow_fallback_chunk:
            raise HTTPException(status_code=422, detail="no_text_extracted")
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script","style","noscript"]):
            t.decompose()
        text = clean_whitespace(soup.get_text(" "))[:1200]
    
    # Sentence split + chunk    
    sentences = split_unicode(text) or [text[:1200]]
    chunks = chunk_by_tokens(
        sentences,
        max_tokens=item.max_tokens,
        overlap=item.overlap
    )
    # Ensure positive token counts (chunker returns (text, tokens))
    chunks = [(c, max(t, len(c.split()))) for (c, t) in chunks]
    if not chunks:
        if not item.allow_fallback_chunk:
            raise HTTPException(status_code=422, detail="no_chunks_made")
        chunks = [(text[:1200], len(text.split()))]
    
    # Embeddings + store
    embeds = await embed_texts([c for c, _ in chunks], model=item.embedding_model)
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
