import os, httpx
from typing import List
import hashlib
import math

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
        # Deterministic, bit-stable pseudo-embeddings via SHA256(text||i).
        out = []
        for t in texts:
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
            out.append(vec)
        return out
    # Online path: deterministic for identical input/model via OpenAI API
    payload = {"input": texts, "model": MODEL}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{OPENAI_BASE}/embeddings", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    return [d["embedding"] for d in data["data"]]
