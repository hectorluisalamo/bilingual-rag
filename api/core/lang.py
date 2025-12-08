import re

_ES_HINTS = re.compile(r"[¿¡ñáéíóúü]|\\b(el|la|de|y|que|cómo|qué)\\b", re.I)
_EN_HINTS = re.compile(r"\\b(the|and|of|how|what|is|are)\\b", re.I)

def detect_lang(text: str) -> str:
    t = text.strip()
    es = bool(_ES_HINTS.search(t))
    en = bool(_EN_HINTS.search(t))
    if es and not en:
        return "es"
    if en and not es:
        return "en"
    if "¿" in t or "¡" in t:
        return "es"
    return "en"