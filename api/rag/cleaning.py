import re

HTML_WHITESPACE = re.compile(r"\s+")
BOILERPLATE = re.compile(r"(cookies|suscríbete|boletín|accesibilidad)", re.I)

def clean_text(text: str) -> str:
    t = HTML_WHITESPACE.sub(" ", text)
    # strip boilerplate repeats
    t = re.sub(r"(Leer más\s*){2,}", "Leer más ", t, flags=re.I)
    return t.strip()

def drop_noise(s: str) -> bool:
    if len(s) < 200:  # too short to be useful as a chunk
        return True
    if BOILERPLATE.search(s):
        return True
    return False

def normalize_lang_tag(lang: str) -> str:
    lang = (lang or "").lower()
    if lang.startswith("es"):
        return "es"
    if lang.startswith("en"):
        return "en"
    return "es"
