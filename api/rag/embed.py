import os, httpx, hashlib, math
from typing import List
import tiktoken

OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBED_DIM = 1536 # text-embedding-3-*
TIMEOUT = httpx.Timeout(float(os.getenv("HTTP_TIMEOUT", "15")), read=float(os.getenv("TOUT_READ", "5")), connect=float(os.getenv("TOUT_CONNECT", "5")))

_headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
_enc = tiktoken.get_encoding("cl100k_base")

def _fallback_embed(texts: List[str], dim: int = EMBED_DIM) -> List[list]:
    vecs = []
    for t in texts:
        v = [0.0] * dim
        for tok in _enc.encode(t or ""):
            h = int(hashlib.md5(str(tok).encode()).hexdigest(), 16)
            v[h % dim] += 1.0
        norm = math.sqrt(sum(x*x for x in v)) or 1.0
        vecs.append([x / norm for x in v])
    return vecs

async def _embed_batch(texts: List[str], model: str) -> List[list]:
    payload = {"input": texts, "model": model}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{OPENAI_BASE}/embeddings", headers=_headers, json=payload)
    # Fast-path success
    if r.status_code == 200:
        data = r.json()
        return [d["embedding"] for d in data["data"]]
    # Surface exact error to logs and fall back
    try:
        err = r.json()
    except Exception:
        err = {"text": r.text}
    raise RuntimeError(f"openai_embed_error:{r.status_code}:{err}")

async def embed_texts(texts: List[str], model: str | None = None) -> List[list]:
    # Normalize inputs (no Nones)
    texts = [t if isinstance(t, str) and t.strip() else " " for t in texts]
    use_model = (model or MODEL).strip()

    # Batch to avoid oversized payload edge cases
    BATCH = 64
    if not API_KEY:
        return _fallback_embed(texts)

    out: List[list] = []
    i = 0
    while i < len(texts):
        batch = texts[i:i+BATCH]
        try:
            out.extend(await _embed_batch(batch, use_model))
        except Exception as e:
            # Fallback deterministically for the entire remaining set
            print(f"[embed] Falling back due to: {e}")
            out.extend(_fallback_embed(batch))
        i += BATCH
    return out
