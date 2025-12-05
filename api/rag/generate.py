from typing import List, Dict, Optional
import anyio, re
from api.core.llm import openai_chat

# --- Helpers 

_WS = re.compile(r"\s+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
# Sentences that look like definitional answers in ES/EN
_DEF_VERBS = re.compile(
    r"\b(es|son|se\s+define\s+como|consiste|es\s+una|es\s+un|is|are|is\s+a|is\s+an)\b",
    re.IGNORECASE,
)

SYS = (
"You are a precise bilingual assistant. Answer ONLY using the provided context. "
"Respond in the language of the question. Each sentence must include citation markers "
"like [1], [2] that map to the numbered sources below. If the context lacks facts, say you "
"don't have enough information."
)

def _norm(s: str) -> str:
    return _WS.sub(" ", (s or "").strip())

def _subject_from_question(q: str) -> Optional[str]:
    q = (q or "").strip().lower().strip("¿? ")
    # Spanish patterns
    m = re.match(r"(que|qué)\s+es\s+(?:una?|el|la|los|las)?\s*(.+)", q)
    if m:
        return _WS.sub(" ", m.group(2)).strip("?.! ")
    # English patterns
    m = re.match(r"what\s+is\s+(?:a|an|the)?\s*(.+)", q)
    if m:
        return _WS.sub(" ", m.group(1)).strip("?.! ")
    return None

# --- Context building ---

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

# --- Rule-based fallback ---

def _first_def_sentence(subject: Optional[str], sims: List[Dict]) -> Optional[str]:
    # Scan top chunks for a subject-containing sentence that looks definitive
    text = " ".join((c.get("text") or c.get("snippet") or "") for c in sims[:5])
    for sent in _SENT_SPLIT.split(text):
        s = _norm(sent)
        if not s:
            continue
        if subject and subject.lower() not in s.lower():
            continue
        if _DEF_VERBS.search(s):
            return s
    return None

def rule_based_definition(question: str, sims: List[Dict]) -> str:
    # Scan top chunks for a definition-like sentence
    subject = _subject_from_question(question)
    candidate = _first_def_sentence(subject, sims)
    if candidate:
        # Best-effort citation (1st matching source)
        return f"{candidate} [1]"
    # Nothing reliable in context
    return "No tengo información suficiente con las fuentes actuales."

# --- Main generator ---

async def quote_then_summarize(question: str, cands: List[Dict]) -> str:
    # Limit context size
    cands = list(cands or [])[:5]
    if not cands:
        return "No tengo información suficiente con las fuentes actuales."
    
    ctx = build_context(cands)
    
    # Extract up to 3 relevant quotes
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
                txt = _norm(item.get("text", ""))
                if 1 <= i <= len(cands) and txt:
                    quotes.append({"i": i, "text": txt})
                if len(quotes) >= 3:
                    break
            except Exception:
                continue
    
    # Early rule-based fallback
    if not quotes:
        return rule_based_definition(question, cands)

    # Summarize in 1-2 sentences with [i] markers
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
    
    # Final rule-based fallback
    return rule_based_definition(question, cands)

