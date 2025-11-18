import os, httpx
from typing import List

OPENAI_BASE = os.getenv("OPENAI_BASE", "https://api.openai.com/v1")
API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

async def embed_texts(texts: List[str]) -> List[list]:
    # deterministic embeddings given same input/model
    payload = {"input": texts, "model": MODEL}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{OPENAI_BASE}/embeddings", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    return [d["embedding"] for d in data["data"]]
