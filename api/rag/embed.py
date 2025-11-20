import os, httpx
from typing import List
import hashlib
import math

OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBED_DIM = 1536 # text-embedding-3-*

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Per-process cache to ensure bit-identical repeat outputs w/in run
_EMBED_CACHE: dict[tuple[str, str], list[float]] = {}

async def embed_texts(texts: List[str], model: str | None = None) -> List[list]:
    use_model = model or MODEL
    # Return any already-cached vectors first
    out: list[list[float]] = []
    missing: list[str] = []
    for t in texts:
        key = (use_model, t)
        if key in _EMBED_CACHE:
            # Copy to avoid external mutation of cache
            out.append(list(_EMBED_CACHE[key]))
        else:
            missing.append(t)
    # If everthing was cached ...
    if len(missing) == 0:
        return out
    if API_KEY:
        # Online path: deterministic for identical input/model via OpenAI API
        payload = {"input": missing, "model": MODEL}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{OPENAI_BASE}/embeddings", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        for t, d in zip(missing, data["data"]):
            _EMBED_CACHE[(MODEL, t)] = d["embedding"]
        return [list(_EMBED_CACHE[(MODEL, t)]) for t in texts]
    else:
        # Deterministic, bit-stable pseudo-embeddings via SHA256(text||i).
        for t in missing:
            vec = []
            te = t.encode("utf-8")
            for i in range(EMBED_DIM):
                # Hash text with 4-byte counter
                h = hashlib.sha256(te + i.to_bytes(4, "big", signed=False)).digest()
                # Map first 8 bytes to [0,1)
                u = int.from_bytes(h[:8], "big", signed=False)
                x = (u / 2**64) # [0,1)
                x = x * 2.0 - 1.0 # [-1,1)
                vec.append(x)
            # L2 normalize
            norm = math.sqrt(sum(v*v for v in vec)) or 1.0
            vec = [v / norm for v in vec]
            _EMBED_CACHE[(MODEL, t)] = vec
        # Merge cached + newly computed in orig order
        return [list(_EMBED_CACHE[(MODEL, t)]) for t in texts]