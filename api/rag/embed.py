import os, httpx
from typing import List
import hashlib
import numpy as np

OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
OFFLINE = os.getenv("OPENAI_OFFLINE_EMBED", "0") == "1"
EMBED_DIM = 1536 # text-embedding-3-*

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

async def embed_texts(texts: List[str]) -> List[list]:
    """
    Returns embeddings.
    - Online: calls OpenAI when API key is present and OFFLINE flag is not set.
    - Offline (CI/local without key): returns deterministic pseudo-embeddings, stable across runs.
    """
    if not API_KEY or OFFLINE:
        # Deterministic pseudo-embedding via SHA256-seeded RNG, normalized.
        out = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            seed = int.from_bytes(h[:8], "big", signed=False) % (2**32)
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(EMBED_DIM).astype(np.float32)
            # L2 normalize
            v = v / max(np.linalg.norm(v), 1e-8)
            out.append(v.tolist())
        return out
    # Online path: deterministic for identical input/model via OpenAI API
    payload = {"input": texts, "model": MODEL}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{OPENAI_BASE}/embeddings", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    return [d["embedding"] for d in data["data"]]
