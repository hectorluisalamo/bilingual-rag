import re, trafilatura
from bs4 import BeautifulSoup
from typing import List, Tuple

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_HTML_WS = re.compile(r"\s+")

def clean_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

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

def extract_html(html: str) -> str:
    # 1) Try trafilatura (article/main content)
    extracted = trafilatura.extract(html, include_comments=False, include_formatting=False, favor_precision=True) or ""
    if len(extracted.strip()) >= 400:
        return _HTML_WS.sub(" ", extracted).strip()
    # 2) Fallback to BeautifulSoup full-text
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]): t.decompose()
    txt = soup.get_text(" ", strip=True)
    return _HTML_WS.sub(" ", txt).strip()

def split_unicode(text: str):
    # Unicode-friendly sentence splitter
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 80]
