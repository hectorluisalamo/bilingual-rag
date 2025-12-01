from typing import List, Dict
import anyio
from api.core.llm import openai_chat

SYS = (
"You are a precise bilingual assistant. Answer ONLY using the provided context. "
"Respond in the language of the question. Each sentence must include citation markers "
"like [1], [2] that map to the numbered sources below. If the context lacks facts, say you "
"don't have enough information."
)

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

