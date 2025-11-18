from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import create_engine
from api.core.config import settings
from api.rag.chunk import split_sentences, chunk_by_tokens
from api.rag.embed import embed_texts
from api.rag.store import upsert_document, insert_chunks
from bs4 import BeautifulSoup
from pdfminer.high_level import extract_text
import httpx

router = APIRouter()
engine = create_engine(settings.db_url, pool_pre_ping=True)

class IngestURL(BaseModel):
    url: str
    lang: str = "es"
    topic: str | None = None
    country: str | None = None
    section: str | None = None

class IngestPDF(BaseModel):
    path: str
    lang: str = "es"
    topic: str | None = None
    country: str | None = None
    section: str | None = None
    

@router.post("/url")
async def ingest_url(item: IngestURL):
    async with httpx.AsyncClient(timeout=30) as client:
        html = (await client.get(item.url)).text
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    sentences = split_sentences(text)
    chunks = chunk_by_tokens(sentences)
    embeds = await embed_texts([chunk for chunk, _ in chunks])
    with engine.begin() as conn:
        doc_id = upsert_document(conn, item.url, "url", item.lang, item.country, item.topic)
        payload = [(chunk, tok_count, e_vector, item.section) for (chunk, tok_count), e_vector in zip(chunks, embeds)]
        insert_chunks(conn, doc_id, payload)
    return {"doc_id": str(doc_id), "chunks": len(chunks)}

@router.post("/pdf")
async def ingest_pdf(item: IngestPDF):
    text = extract_text(item.path)
    sentences = split_sentences(text)
    chunks = chunk_by_tokens(sentences)
    embeds = await embed_texts([chunk for chunk, _ in chunks])
    with engine.begin() as conn:
        doc_id = upsert_document(conn, item.path, "pdf", item.lang, item.country, item.topic)
        payload = [(chunk, tok_count, e_vector, item.section) for (chunk, tok_count), e_vector in zip(chunks, embeds)]
        insert_chunks(conn, doc_id, payload)
    return {"doc_id": str(doc_id), "chunks": len(chunks)}
