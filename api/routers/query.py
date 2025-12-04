from contextlib import asynccontextmanager
from fastapi import APIRouter
from typing import Annotated, List, Mapping, Optional
from pydantic import BaseModel, StringConstraints, Field, model_validator
from api.core.config import settings
from api.rag.embed import embed_texts
from api.rag.retrieve import search_similar
from api.rag.router import load_faq
from api.routers.metrics import REQUESTS, LATENCY, EMB_LAT, DB_LAT
import asyncio, unicodedata, re, time, os, logging, uuid


@asynccontextmanager
async def lifespan(app: APIRouter):
    global FAQ
    try:
        FAQ = load_faq(settings.router_faq_path)
    except FileNotFoundError:
        FAQ = {}
    yield
    
router = APIRouter(lifespan=lifespan)

FAQ = None
NORM_WS = re.compile(r"\s+")
VALID_TOPICS = {"food","culture","health","civics","education"}
QUERY_TIMEOUT_SEC = int(os.getenv("QUERY_TIMEOUT_SEC", "8"))
Q_LOGGER = logging.getLogger("api.query")


class Query(BaseModel):
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
async def ask(payload: Query):
    rid = str(uuid.uuid4())
    q = normalize_query(payload.query)
    index_name = payload.index_name or os.getenv("DEFAULT_INDEX_NAME", "c300o45")
    lang = payload.lang_pref
    cites: List[dict] = []
    
    # Test mode for CI
    if os.getenv("TEST_MODE") == "1":
        return {
            "route": "test_stub",
            "answer": f"Echo: {q}",
            "citations": [],
            "request_id": rid
            }
    async def _query_task():
        sims: List = []
        answer: str = ""
        Q_LOGGER.info("req start id=%s q=%r k=%s lang=%s rerank=%s index=%s",
            rid, q, payload.k, lang, payload.use_reranker, index_name)
        
        try:
            t0 = time.time()     
            # Embed
            e0 = time.time()
            embs = await embed_texts([q])
            EMB_LAT.observe((time.time() - e0) * 1000)
            qvec = embs[0]
            Q_LOGGER.debug("embed ok id=%s dim=%s", rid, len(qvec) if embs and qvec else None)
   
            # Retrieve
            s0 = time.time()
            sims = search_similar(
                qvec,
                k=max(payload.k, 8),
                lang_filter=tuple(lang or ("es", "en")),
                topic=payload.topic_hint,
                country=payload.country_hint,
                index_name=index_name
            )
            Q_LOGGER.debug("retrieved=%d id=%s", len(sims or []), rid)
            if sims:
                first = sims[0]
                if isinstance(first, dict):
                    Q_LOGGER.debug("sims0: dict keys=%s id=%s", list(first.keys()), rid)
                else:
                    Q_LOGGER.debug("sims0: type=%s has_text=%s id=%s", type(first).__name__, hasattr(first, "text"), rid)

            # Fallback if empty
            if not sims:
                sims = search_similar(
                    qvec,
                    k=max(payload.k, 8),
                    lang_filter=("es", "en"),
                    topic=None,
                    country=payload.country_hint,
                    index_name=index_name
                )
            DB_LAT.observe((time.time() - s0) * 1000)
            Q_LOGGER.debug("retrieved=%d id=%s", len(sims or []), rid)
        
            # Guarded reranker
            sims = [s for s in (sims or []) if _as_text(s)]
            Q_LOGGER.debug("post-filter=%d id=%s", len(sims), rid)

            use_reranker = bool(payload.use_reranker) and os.getenv("RERANK_ENABLED", "0") in ("1","true","True")
            if use_reranker and sims:
                Q_LOGGER.debug("rerank start id=%s", rid)
                # Ensure each item has a string to rank
                from api.rag.rerank import rerank
                sims = rerank(q, sims, top_k=payload.k)
                Q_LOGGER.debug("rerank done n=%d id=%s", len(sims), rid)
            else:
                sims = sims[: payload.k]
            
            # Build citations safely
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
        
            # Metrics (after success)
            LATENCY.observe((time.time() - t0) * 1000)
            REQUESTS.labels(route="rag", index=index_name, topic=str(payload.topic_hint), lang=lang).inc()

            return {"route": "rag", "answer": answer, "citations": cites, "request_id": rid}
        
        except Exception as e:
            Q_LOGGER.exception("query_failed id=%s etype=%s", rid, type(e).__name__)
            # IMPORTANT: return schema (status 200), not HTTPException/detail
            return {
                "route": "error",
                "answer": "",
                "citations": [],
                "request_id": rid,
                "error": {"code":"internal_error","type":type(e).__name__}
            }
        
    try:
        result = await asyncio.wait_for(_query_task(), timeout=QUERY_TIMEOUT_SEC)
        return result
    except asyncio.TimeoutError:
        Q_LOGGER.warning("query_timeout id=%s budget=%ss", rid, QUERY_TIMEOUT_SEC)
        # Still return schema-shape so UI doesn’t crash
        return {"route":"timeout","answer":"","citations":[],"request_id":rid,"error":{"code":"timeout"}}
    
@router.post("/echo")
async def echo(payload: Query):
    return {"ok": True, "received": payload.model_dump()}
