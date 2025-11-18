import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

_tokenizer = None
_model = None

def get_model(name="BAAI/bge-reranker-base"):
    global _tokenizer, _model
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(name)
        _model = AutoModelForSequenceClassification.from_pretrained(name)
        _model.eval()
    return _tokenizer, _model

def rerank(query: str, passages: list, top_k: int = 5):
    tok, model = get_model()
    pairs = [(query, p["text"]) for p in passages]
    inputs = tok.batch_encode_plus(pairs, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        scores = model(**inputs).logits.squeeze(-1)
    ranked = sorted(zip(passages, scores.tolist()), key=lambda x: x[1], reverse=True)
    return [p for p, _ in ranked[:top_k]]
