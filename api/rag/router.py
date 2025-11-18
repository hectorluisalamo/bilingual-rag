import json, re
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
    faq = {}
    with open(path) as f:
        for line in f:
            obj = json.loads(line)
            faq[obj["q"].strip().lower()] = obj["a"]
    return faq
