from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, Request
from typing import Annotated
from pydantic import BaseModel, StringConstraints, Field
from api.core.config import settings
from api.rag.embed import embed_texts
from api.rag.retrieve import search_similar
from api.rag.rerank import rerank
from api.rag.router import load_faq, route
import unicodedata, re, asyncio, structlog


@asynccontextmanager
async def lifespan(app: APIRouter):
    global FAQ
    try:
        FAQ = load_faq(settings.router_faq_path)
    except FileNotFoundError:
        FAQ = {}
    yield
    

router = APIRouter(lifespan=lifespan)
log = structlog.get_logger(__name__)
FAQ = None
NORM_WS = re.compile(r"\s+")


class QueryIn(BaseModel):
    query: Annotated[str, StringConstraints(min_length=2, max_length=512)]
    k: int = Annotated[str, Field(5, ge=1, le=8)]
    lang_pref: list[str] = ["en", "es"]
    use_reranker: bool = True
    topic_hint: str | None = None
    country_hint: str | None = None
    index_name: str = settings.default_index_name
    
class Citation(BaseModel):
    uri: str
    snippet: str
    date: str | None = None
    score: float | None = None

class QueryOut(BaseModel):
    route: str
    answer: str
    citations: list[dict]
    
    
def normalize_query(q: str) -> str:
    q = unicodedata.normalize("NFKC", q)
    q = NORM_WS.sub(" ", q).strip()
    return q


@router.post("", response_model=QueryOut)
@router.post("/", response_model=QueryOut)
async def ask(req: Request, payload: QueryIn):
    rid = getattr(req.state, "request_id", "na")
    q = normalize_query(payload.query)
    try:
        rtype, why = route(q, FAQ)
        if rtype == "faq":
            return QueryOut(route="faq", answer=FAQ[q.lower()], citations=[], request_id=rid)
   
        # embeddings (one retry on 429/5xx)
        try:
            embs = await embed_texts([q])
        except Exception:
            await asyncio.sleep(0.4)
            embs = await embed_texts([q])
            
        sims = search_similar(
            embs[0],
            k=max(payload.k, 8),
            lang_filter=tuple(payload.lang_pref),
            topic=payload.topic_hint,
            country=payload.country_hint,
            index_name=payload.index_name
        )
        if payload.use_reranker and sims:
            sims = rerank(q, sims, top_k=payload.k)
        else:
            sims = sims[:payload.k]
        
        answer = f"Encontré {len(sims)} pasajes relevantes."
        cites = [
            {"uri": s["source_uri"], "snippet": s["text"][:220], "date": str(s["published_at"]), "score": s.get("score")}
            for s in sims
        ]
        
        log.info("query", request_id=rid, route=rtype, k=payload.k, index=payload.index_name,
                topic=payload.topic_hint, langs=payload.lang_pref, ms=req.state.duration_ms)
    
        return QueryOut(route="rag", answer=answer, citations=cites, request_id=rid)
    
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail={"code":"timeout","message":"upstream timeout"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code":"internal_error","message":type(e).__name__})

@router.post("/echo")
async def echo(payload: QueryIn):
    return {"ok": True, "received": payload.model_dump()}
