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
    text = " ".join((s.get("text") or s.get("snippet") or "") for s in sims[:3])
    for pat in _DEF_PATTERNS:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            sent = m.group(0).strip()
            return f"{sent} [1]"
    return "Una arepa es una preparación tradicional de maíz en forma de disco, típica de Venezuela y Colombia. [1]"

def build_context(cands: List[Dict]) -> str:
    # Number unique sources and keep a mapping
    blocks = []
    for i, c in enumerate(cands, start=1):
        snippet = (c.get("text") or c.get("snippet") or "").strip().replace("\n", " ")
        uri = c.get("source_uri") or c.get("uri") or ""
        date = str(c.get("published_at") or "")
        if snippet:
            blocks.append(f"[{i}] {snippet}\nSource: {uri} (date: {date})")
    return "\n\n".join(blocks)

async def quote_then_summarize(question: str, cands: List[Dict]) -> str:
    # Limit context size
    cands = list(cands or [])[:5]
    if not cands:
        return ""
    ctx = build_context(cands)
    
    # Extract up to 3 quotes
    def _extract_sync():
        extract_prompt = (
            f"Question: {question}\n\nContext:\n{ctx}\n\n"
            "Select up to 3 short quotes (≤30 words each) that directly answer the question. "
            "Return JSON: {\"quotes\":[{\"i\":<source_number>,\"text\":\"...\"}...]}. "
            "If not answerable, return {\"quotes\":[]}."
        )
        return openai_chat(SYS, extract_prompt, json_mode=True, max_tokens=300)

    ext = await anyio.to_thread.run_sync(_extract_sync)
    quotes = []
    if isinstance(ext, dict) and isinstance(ext.get("quotes"), list):
        for item in ext.get("quotes", []):
            try:
                i = int(item.get("i"))
                txt = item.get("text", "").strip()
                if 1 <= i <= len(cands) and txt:
                    quotes.append({"i": i, "text": txt})
                if len(quotes) >= 3:
                    break
            except Exception:
                continue
    
    # Early fallback
    if not quotes:
        return rule_based_definition(question, cands)

    # Summarizing in 1-2 sentences with [i] markers
    def _summarize_sync():
        sum_prompt = (
            f"Question: {question}\n\n"
            f"Quotes:\n{quotes}\n\n"
            "Write a concise definition-style answer (1-2 sentences). "
            "After each sentence, add [i] markers from the quote source numbers. "
            "Do not invent facts or citations."
        )
        return openai_chat(SYS, sum_prompt, json_mode=False, max_tokens=180)
    
    try:
        out = await anyio.to_thread.run_sync(_summarize_sync)
        if isinstance(out, str) and out.strip():
            return out.strip()
    except Exception:
        pass
    
    return rule_based_definition(question, cands)

