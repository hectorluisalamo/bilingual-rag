from fastapi import APIRouter
from pydantic import BaseModel
from api.core.db import engine
from api.rag.chunk import split_sentences, chunk_by_tokens
from api.rag.cleaning import clean_text, drop_noise, normalize_lang_tag
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
    html_text = BeautifulSoup(raw, "html.parser").get_text(" ")
    text = clean_text(html_text)
    sentences = [s for s in split_sentences(text) if not drop_noise(s)]
    chunks = chunk_by_tokens(
        sentences,
        max_tokens=item.max_tokens,
        overlap=item.overlap
    )
    embeds = await embed_texts([c for c,_ in chunks], model=item.embedding_model)
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
