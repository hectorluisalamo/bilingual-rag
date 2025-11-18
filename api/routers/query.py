from contextlib import asynccontextmanager
from fastapi import APIRouter
from pydantic import BaseModel
from api.core.config import settings
from api.rag.embed import embed_texts
from api.rag.retrieve import search_similar
from api.rag.rerank import rerank
from api.rag.router import load_faq, route

FAQ = None

@asynccontextmanager
async def lifespan(app: APIRouter):
    global FAQ
    try:
        FAQ = load_faq(settings.router_faq_path)
    except FileNotFoundError:
        FAQ = {}
    yield


router = APIRouter(lifespan=lifespan)


class QueryIn(BaseModel):
    query: str
    k: int = 6
    lang_pref: list[str] = ["en", "es"]
    use_reranker: bool = True

class QueryOut(BaseModel):
    route: str
    answer: str
    citations: list[dict]

@router.post("/", response_model=QueryOut)
async def ask(payload: QueryIn):
    rtype, why = route(payload.query, FAQ)
    if rtype == "faq":
        return QueryOut(route="faq", answer=FAQ[payload.query.strip().lower()], citations=[])
    # memory_only path elided in MVP
    embs = await embed_texts([payload.query])
    sims = search_similar(embs[0], k=max(payload.k, 8), lang_filter=tuple(payload.lang_pref))
    if payload.use_reranker and sims:
        sims = rerank(payload.query, sims, top_k=payload.k)
    # naïve generator placeholder with per-claim-ish cites
    answer = f"Here's what I found for '{payload.query}' (languages {payload.lang_pref})."
    cites = [
        {"uri": s["source_uri"], "snippet": s["text"][:180], "date": str(s["published_at"]), "score": s["score"]}
        for s in sims[:payload.k]
    ]
    return QueryOut(route="rag", answer=answer, citations=cites)
