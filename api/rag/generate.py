from typing import List, Dict
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
    extract_prompt = (
        f"Question: {question}\n\nContext:\n{ctx}\n\n"
        "Select 3 short quotes (max 30 words each) that directly answer the question. "
        "Return JSON: {\"quotes\":[{\"i\":<source_number>,\"text\":\"...\"}...]}. "
        "If not answerable, return {\"quotes\":[]}."
    )
    # sync wrapper
    ext = await openai_chat(SYS, extract_prompt, json_mode=True)
    quotes = ext.get("quotes", [])[:5]

    # 2) Abstractive – write 1–3 sentences with cite markers
    sum_prompt = (
        f"Question: {question}\n\nQuotes:\n{quotes}\n\n"
        "Write a concise answer (1–3 sentences). After each sentence, add [i] markers "
        "using the source numbers from the quotes. Do not invent citations."
    )
    text = await openai_chat(SYS, sum_prompt)
    return {"text": text, "quotes": quotes}
