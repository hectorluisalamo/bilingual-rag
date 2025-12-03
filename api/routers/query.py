from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, Request
from typing import Annotated, List
from pydantic import BaseModel, StringConstraints, Field, model_validator
from api.core.config import settings
from sqlalchemy.exc import OperationalError
from api.rag.embed import embed_texts
from api.rag.generate import quote_then_summarize, rule_based_definition
from api.rag.retrieve import search_similar, dedup_by_uri, prefer_entity
from api.rag.rerank import rerank
from api.rag.router import load_faq, route
from api.routers.metrics import REQUESTS, ERRORS, LATENCY, EMB_LAT, DB_LAT
import unicodedata, re, asyncio, structlog, time


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
    return 

def _select_sentences(query: str, texts: list[str], max_sentences: int = 3) -> list[str]:
    q_tokens = set(re.findall(r"\w+", (query or "").lower()))
    candidates: list[tuple[int,str]] = []
    for t in texts:
        if not isinstance(t, str):
            continue
        for s in re.split(r"(?<=[.!?])\s+", t):
            st = (s or "").strip()
            if not st:
                continue
            s_tokens = set(re.findall(r"\w+", st.lower()))
            score = len(q_tokens & s_tokens)
            candidates.append((score, st))
    candidates.sort(reverse=True, key=lambda x: x[0])
    out: list[str] = []
    for _, s in candidates:
        if all(s not in o and o not in s for o in out):
            out.append(s)
        if len(out) >= max_sentences:
            break
    return out


@router.post("", response_model=QueryOut)
@router.post("/", response_model=QueryOut)
async def ask(req: Request, payload: QueryIn):
    rid = getattr(req.state, "request_id", "na")
    q = normalize_query(payload.query)
    t0 = time.time()
    
    # Normalize langs; guard empty
    langs = [s.lower().strip() for s in (payload.lang_pref or []) if s]
    if not langs:
        langs = ["es", "en"]
        
    try:
        # 1) FAQ short-circuit
        rtype, _ = route(q, FAQ)
        if rtype == "faq":
            REQUESTS.labels(route="faq", index=payload.index_name, topic=str(payload.topic_hint), langs=",".join(langs)).inc()
            LATENCY.observe((time.time() - t0) * 1000)
            return QueryOut(route="faq", answer=FAQ[q.lower()], citations=[], request_id=rid)
   
        # 2) Embed (one retry)
        e0 = time.time()
        try:
            embs = await embed_texts([q])
        except Exception:
            await asyncio.sleep(0.4)
            embs = await embed_texts([q])
        EMB_LAT.observe((time.time() - e0) * 1000)
        if not embs or not isinstance(embs, list) or embs[0] is None:
            raise HTTPException(status_code=503, detail={"code": "embeddings_unavailable", "message": "no_vector", "request_id": rid})
        
        qvec = embs[0]
            
        # 3) Retrieve (retry once)
        top_k = min(max(payload.k, 5), 8)
        s0 = time.time()
        try:
            sims = search_similar(
                qvec,
                k=top_k,
                lang_filter=tuple(langs),
                topic=payload.topic_hint,
                country=payload.country_hint,
                index_name=payload.index_name
            )
        except OperationalError:
            await asyncio.sleep(0.2)
            sims = search_similar(
                embs[0],
                k=top_k,
                lang_filter=tuple(langs),
                topic=payload.topic_hint,
                country=payload.country_hint,
                index_name=payload.index_name
            )
        DB_LAT.observe((time.time() - s0) * 1000)
        sims = sims or []
        
        # 4) Rerank / slice
        if payload.use_reranker and sims:
            # ensure each item has a string to rank
            sims = [s for s in sims if isinstance((s.get("text","") if isinstance(s, dict) else getattr(s,"text","")), str)]
            sims = rerank(q, sims, top_k)
        else:
            sims = sims[top_k]
            
        sims = [s for s in sims if (s.get("score") or 0) >= 0.35]
        sims = prefer_entity(sims, q)
        sims = dedup_by_uri(sims)[:top_k]
        
        top_texts = []
        for s in sims[:top_k]:
            txt = s.get("text") if isinstance(s, dict) else getattr(s, "text", None)
            if not isinstance(txt, str) or not txt.strip():
                txt = (s.get("snippet") if isinstance(s, dict) else getattr(s, "snippet", None)) or ""
            top_texts.append(txt)

        best = _select_sentences(q, top_texts, max_sentences=3)
        if best:
            answer = " ".join(best) + " " + " ".join(f"[{i+1}]" for i in range(min(len(sims), top_k)))
        else:
            answer = "No tengo información suficiente con las fuentes actuales."
            
        # 5) Generation w/ guard against None
        try:
            ans = await quote_then_summarize(q, sims)
            answer = (ans or {}).get("text")
        except Exception:
            answer = None
            
        if not answer or len(answer.strip()) < 10:
            answer = rule_based_definition(q, sims)
            
        # Cap outgoing citations
        cites = [
            {"uri": s["source_uri"], 
             "snippet": (s.get("text", "") or "")[:220], 
             "date": str(s.get("published_at")) if s.get("published_at") is not None else None, 
             "score": s.get("score")}
            for s in sims
        ]
        
        # 6) Logging + metrics (after success)
        log.info(
            "query",
            request_id=rid, 
            route="rag", 
            k=top_k, 
            index=payload.index_name,
            topic=payload.topic_hint, 
            langs=langs,
            ms=getattr(req.state, "duration_ms", int((time.time() - t0) * 1000))
        )
        LATENCY.observe((time.time() - t0) * 1000)
        REQUESTS.labels(route="rag", index=payload.index_name, topic=str(payload.topic_hint), langs=",".join(langs)).inc()
    
        return QueryOut(route="rag", answer=answer, citations=cites, request_id=rid)
    
    except HTTPException:
        raise
    except Exception as e:
        # Dev-friendly error message if enabled
        msg = repr(e) if settings.dev_errors else type(e).__name__
        raise HTTPException(status_code=500, detail={"code":"internal_error","message":msg,"request_id":rid})

        
@router.post("/echo")
async def echo(payload: QueryIn):
    return {"ok": True, "received": payload.model_dump()}
