import os
from typing import List, Mapping, Any


_RERANK_AVAIL = None
_tokenizer = None
_model = None

def _maybe_load():
    global _RERANK_AVAIL, _tokenizer, _model
    if _RERANK_AVAIL is not None:
        return _RERANK_AVAIL
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer  # type: ignore
        model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForSequenceClassification.from_pretrained(model_name)
        _RERANK_AVAIL = True
    except Exception:
        _RERANK_AVAIL = False
    return _RERANK_AVAIL

def rerank(query: str, items: List[Mapping[str, Any]], top_k: int = 5):
    # Fast no-op if disabled or unavailable
    if not os.getenv("RERANK_ENABLED", "0") in ("1", "true", "True"):
        return items[:top_k]
    if not _maybe_load():
        return items[:top_k]

    # Minimal scoring (batching omitted for brevity)
    from torch.nn.functional import softmax  # lazy import; works if torch present
    import torch

    pairs = [f"{query} [SEP] { (i.get('text') or i.get('snippet') or '') }" for i in items]
    inputs = _tokenizer(pairs, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        logits = _model(**inputs).logits
        probs = softmax(logits, dim=1)[:, 1]  # assume class 1 = relevant
    scored = list(zip(items, probs.tolist()))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [it for it, _ in scored[:top_k]]