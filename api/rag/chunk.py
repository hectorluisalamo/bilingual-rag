import re
from typing import List, Tuple

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]

def chunk_by_tokens(sentences: List[str], max_tokens: int = 600, overlap: int = 60, count_tokens=lambda x: len(x.split())) -> List[Tuple[str, int]]:
    chunks, buf, buf_tokens = [], [], 0
    for s in sentences:
        t = count_tokens(s)
        if buf_tokens + t > max_tokens and buf:
            chunk_text = " ".join(buf)
            chunks.append((chunk_text, buf_tokens))
            # overlap
            while buf and buf_tokens > overlap:
                buf_tokens -= count_tokens(buf.pop(0))
        buf.append(s)
        buf_tokens += t
    if buf:
        chunks.append((" ".join(buf), buf_tokens))
    return chunks
