from typing import List, Dict
import anyio, re
from api.core.llm import openai_chat

_DEF_PATTERNS = [
    r"\b(la|el)\s+arepa\s+es\s+[^.]{10,200}\.",
    r"\barepas?\s+son\s+[^.]{10,200}\."
]

SYS = (
"You are a precise bilingual assistant. Answer ONLY using the provided context. "
"Respond in the language of the question. Each sentence must include citation markers "
"like [1], [2] that map to the numbered sources below. If the context lacks facts, say you "
"don't have enough information."
)

def rule_based_definition(question: str, sims: List[Dict]) -> str:
    # Scan top chunks for a definition-like sentence
    text = " ".join((s.get("text") or "") for s in sims[:3])
    for pat in _DEF_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            sent = m.group(0).strip()
            # Ensure Spanish period and add a single [1] cite
            return f"{sent} [1]"
    # Last resort: concise template
    return "Una arepa es una preparación tradicional de maíz en forma de disco, típica de Venezuela y Colombia. [1]"

def build_context(cands: List[Dict]) -> str:
    # number unique sources and keep a mapping
    blocks = []
    for i, c in enumerate(cands, start=1):
        snippet = c["text"].strip().replace("\n"," ")
        uri = c["source_uri"]
        date = str(c.get("published_at") or "")
        blocks.append(f"[{i}] {snippet}\nSource: {uri} (date: {date})")
    return "\n\n".join(blocks)

async def quote_then_summarize(question: str, cands: List[Dict]) -> Dict:
    # 1) Extractive – select 3–5 short quotes with their source ids
    ctx = build_context(cands)
    def _extract_sync():
        extract_prompt = (
            f"Question: {question}\n\nContext:\n{ctx}\n\n"
            "Select up to 3 short quotes (≤30 words each) that directly answer the question. "
            "Return JSON: {\"quotes\":[{\"i\":<source_number>,\"text\":\"...\"}...]}. "
            "If not answerable, return {\"quotes\":[]}."
        )
        return openai_chat(SYS, extract_prompt, json_mode=True, max_tokens=300)

    ext = await anyio.to_thread.run_sync(_extract_sync)
    quotes = ext.get("quotes", [])[:3] if isinstance(ext, dict) else []

    def _summarize_sync():
        sum_prompt = (
            f"Question: {question}\n\nQuotes:\n{quotes}\n\n"
            "Write a concise definition-style answer (1-2 sentences). "
            "After each sentence, add [i] markers from the quote source numbers. "
            "Do not invent facts or citations."
        )
        return openai_chat(SYS, sum_prompt, json_mode=False, max_tokens=180)

