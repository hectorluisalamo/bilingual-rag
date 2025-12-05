import json, re, os
from typing import Literal

INJECTION = re.compile(r"ignore previous|system prompt|do anything now", re.I)

def route(query: str, faq_index: dict) -> tuple[Literal["faq","rag","memory_only"], str]:
    if INJECTION.search(query):
        return "rag", "guarded"
    if query.strip().lower() in faq_index:
        return "faq", "exact match"
    if len(query) < 12:
        return "memory_only", "short utterance"
    return "rag", "default"

def load_faq(path: str) -> dict:
    if not path:
        return {}
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)
