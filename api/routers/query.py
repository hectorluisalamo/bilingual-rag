from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, Request
from typing import Annotated
from pydantic import BaseModel, StringConstraints, Field, model_validator
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
VALID_TOPICS = {"food","culture","health","civics","education"}


class QueryIn(BaseModel):
    query: Annotated[str, StringConstraints(min_length=2, max_length=512)]
    k: int = Field(5, ge=1, le=8)
    lang_pref: list[str] = ["en", "es"]
    use_reranker: bool = True
    topic_hint: str | None = None
    country_hint: str | None = None
    index_name: str = settings.default_index_name
    
    @model_validator(mode="after")
    def _validate_hints(self):
        if self.topic_hint and self.topic_hint not in VALID_TOPICS:
            raise ValueError(f"topic_hint must be one of {sorted(VALID_TOPICS)}")
        return self
    
class Citation(BaseModel):
    uri: str
    snippet: str
    date: str | None = None
    score: float | None = None

class QueryOut(BaseModel):
    route: str
    answer: str
    citations: list[dict]
    request_id: str
    
    
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
        rtype, _ = route(q, FAQ)
        if rtype == "faq":
            return QueryOut(route="faq", answer=FAQ[q.lower()], citations=[], request_id=rid)
   
        # embeddings (one retry)
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
        top_k = max(1, payload.k) # guard against k=0
        if payload.use_reranker and sims:
            sims = rerank(q, sims, top_k=top_k)
        else:
            sims = sims[:top_k]
        
        # Build grounded answer from first sentence
        def first_sentence(txt: str, max_chars: int = 240) -> str:
            s = (txt or "").strip()
            cut = s.split(". ")[0]
            cut = cut if cut else s[:max_chars]
            return cut[:max_chars].strip()

        if sims:
            top_snip = sims[0]["text"]
            answer = first_sentence(top_snip)
        else:
            answer = "No encontré pasajes relevantes para esta consulta."
            
        cites = [
            {
                "uri": s["source_uri"], 
                "snippet": s["text"][:220], 
                "date": str(s["published_at"]), 
                "score": s.get("score")}
            for s in sims
        ]
        
        log.info("query",
                 request_id=rid, 
                 route=rtype, 
                 k=top_k, 
                 index=payload.index_name,
                 topic=payload.topic_hint, 
                 langs=payload.lang_pref,
                 ms=getattr(req.state, "duration_ms", 0))
    
        return QueryOut(route="rag", answer=answer, citations=cites, request_id=rid)
    
    except ValueError as ve:
        raise HTTPException(status_code=422, detail={"code":"validation_error","message":str(ve)})
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail={"code":"timeout","message":"upstream timeout"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code":"internal_error","message":type(e).__name__})

@router.post("/echo")
async def echo(payload: QueryIn):
    return {"ok": True, "received": payload.model_dump()}
