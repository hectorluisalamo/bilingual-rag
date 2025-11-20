from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.core.db import engine
from api.rag.chunk import split_sentences, chunk_by_tokens, extract_text, split_sentences_unicode
from api.rag.cleaning import clean_text
from api.rag.embed import embed_texts
from api.rag.fetch import fetch_text
from api.rag.store import upsert_document, insert_chunks
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
from sqlalchemy import text as sqltext

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
    raw = await fetch_text(item.url, accept_lang=item.lang)
    text = extract_text(raw)
    if not text or len(text) < 200:
        if item.allow_fallback_chunk:
            # Store first 1200 chars as single chunk
            text = (text or BeautifulSoup(raw, "html.parser").get_text(" "))
            text = clean_text(text)
        else:
            raise HTTPException(status_code=422, detail="no_text_extracted")
    
    # Sentence split + chunk    
    sentences = split_sentences_unicode(text)
    if not sentences:
        sentences = [text[:1200]]
    chunks = chunk_by_tokens(
        sentences,
        max_tokens=item.max_tokens,
        overlap=item.overlap
    )
    # Ensure positive token counts (chunker returns (text, tokens))
    chunks = [(c, max(t, len(c.split()))) for (c, t) in chunks]
    if not chunks:
        if item.allow_fallback_chunk:
            chunks = [(text[: min(len(text), 1200)], len(text.split()))]
        else:
            raise HTTPException(status_code=422, detail="no_chunks_made")
    
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

@router.post("/pdf")
async def ingest_pdf(item: IngestPDF):
    text = extract_text(item.path)
    sentences = split_sentences(text)
    chunks = chunk_by_tokens(
        sentences,
        max_tokens=item.max_tokens,
        overlap=item.overlap
    )
    if not chunks:
        raise HTTPException(status_code=422, detail="no_chunks_made")
    embeds = await embed_texts([c for c,_ in chunks], model=item.embedding_model)
    with engine.begin() as conn:
        doc_id = upsert_document(conn, item.path, "pdf", item.lang, item.country, item.topic, index_name=item.index_name)
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
