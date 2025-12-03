from contextlib import asynccontextmanager
from fastapi import APIRouter, HTTPException, Request
from typing import Annotated, List, Mapping, Optional
from pydantic import BaseModel, StringConstraints, Field, model_validator
from api.core.config import settings
from sqlalchemy.exc import OperationalError
from api.rag.embed import embed_texts
from api.rag.generate import quote_then_summarize, rule_based_definition
from api.rag.retrieve import search_similar, dedup_by_uri, prefer_entity
from api.rag.rerank import rerank
from api.rag.router import load_faq, route
from api.routers.metrics import REQUESTS, ERRORS, LATENCY, EMB_LAT, DB_LAT
import unicodedata, re, asyncio, structlog, time, os


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
    topic_hint: Optional[str] = None
    country_hint: Optional[str] = None
    index_name: Optional[str] = None
    
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


def _as_text(x) -> str:
    # Accept dict-like rows or ORM objects; fallback to snippet
    if isinstance(x, Mapping):
        t = x.get("text")
        if isinstance(t, str) and t.strip():
            return t
        s = x.get("snippet")
        return s if isinstance(s, str) else ""
    # object with attributes
    t = getattr(x, "text", None)
    if isinstance(t, str) and t.strip():
        return t
    s = getattr(x, "snippet", "")
    return s if isinstance(s, str) else ""

def _select_sentences(query: str, texts: List[str], max_sentences: int = 3) -> List[str]:
    q_tokens = set(re.findall(r"\w+", (query or "").lower()))
    candidates = []
    for t in texts:
        if not isinstance(t, str) or not t.strip():
            continue
        for s in re.split(r"(?<=[.!?])\s+", t):
            st = (s or "").strip()
            if not st:
                continue
            s_tokens = set(re.findall(r"\w+", st.lower()))
            score = len(q_tokens & s_tokens)
            candidates.append((score, st))
    candidates.sort(key=lambda x: x[0], reverse=True)
    out = []
    for _, s in candidates:
        if all(s not in o and o not in s for o in out):
            out.append(s)
        if len(out) >= max_sentences:
            break
    return out


@router.post("")
@router.post("/")
async def ask(req: Request, payload: QueryIn):
    rid = getattr(req.state, "request_id", "na")
    
    # --- TEST MODE ---
    if os.getenv("TEST_MODE") == "1":
        return {
            "route": "test_stub",
            "answer": f"Echo: {payload.query}",
            "citations": [],
            "request_id": rid
        }
        
    q = normalize_query(payload.query)
    t0 = time.time()
    
    # Normalize langs; guard empty
    langs = [s.lower().strip() for s in (payload.lang_pref or []) if s]
    if not langs:
        langs = ["es", "en"]
    
    index_name = payload.index_name or os.getenv("DEFAULT_INDEX_NAME", "c300o45")
    
    try:
        # FAQ short-circuit
        rtype, _ = route(q, FAQ)
        if rtype == "faq":
            REQUESTS.labels(route="faq", index=index_name, topic=str(payload.topic_hint), langs=",".join(langs)).inc()
            LATENCY.observe((time.time() - t0) * 1000)
            return QueryOut(route="faq", answer=FAQ[q.lower()], citations=[], request_id=rid)
   
        # Embed
        e0 = time.time()
        embs = await embed_texts([q])
        EMB_LAT.observe((time.time() - e0) * 1000)
        
        qvec = embs[0]
            
        # Retrieve
        top_k = max(payload.k, 8)
        s0 = time.time()
        sims = search_similar(
            qvec,
            k=top_k,
            lang_filter=tuple(langs),
            topic=payload.topic_hint,
            country=payload.country_hint,
            index_name=index_name
        )

        # Fallback if empty
        if not sims:
            sims = search_similar(
                qvec,
                k=top_k,
                lang_filter=tuple(langs),
                topic=None,
                country=payload.country_hint,
                index_name=index_name
            )
        DB_LAT.observe((time.time() - s0) * 1000)
        
        # Guarded reranker
        if payload.use_reranker and sims:
            # Ensure each item has a string to rank
            sims = [s for s in sims if _as_text(s)]
            sims = rerank(q, sims, top_k=top_k)
        else:
            sims = sims[: top_k]
            
        # Build citations safely
        cites = []
        for s in sims:
            if isinstance(s, Mapping):
                cites.append({
                    "uri": s.get("source_uri") or s.get("uri") or "",
                    "snippet": _as_text(s)[:500],
                    "date": s.get("published_at"),
                    "score": s.get("score"),
                })
            else:
                cites.append({
                    "uri": getattr(s, "source_uri", "") or getattr(s, "uri", ""),
                    "snippet": _as_text(s)[:500],
                    "date": getattr(s, "published_at", None),
                    "score": getattr(s, "score", None),
                })

        # Extractive answer (never raises)
        top_texts = [_as_text(s) for s in sims]
        sentences = _select_sentences(q, top_texts, max_sentences=3)
        if sentences:
            answer = (" ".join(sentences) + " " + " ".join(f"[{i+1}]" for i in range(len(cites))))
        else:
            answer = "No tengo información suficiente con las fuentes actuales."
        
        # Logging + metrics (after success)
        log.info(
            "query",
            request_id=rid, 
            route="rag", 
            k=top_k, 
            index=index_name,
            topic=payload.topic_hint, 
            langs=langs,
            ms=getattr(req.state, "duration_ms", int((time.time() - t0) * 1000))
        )
        LATENCY.observe((time.time() - t0) * 1000)
        REQUESTS.labels(route="rag", index=index_name, topic=str(payload.topic_hint), langs=",".join(langs)).inc()
    
        return {route: "rag", "answer": answer, "citations": cites, "request_id": rid}
    
    except Exception as e:
        # Structured error if not TEST_MODE
        raise HTTPException(status_code=200, detail={
            "code": "graceful_error",
            "message": type(e).__name__,
            "request_id": rid
        })
        
@router.post("/echo")
async def echo(payload: QueryIn):
    return {"ok": True, "received": payload.model_dump()}
