import os
from api.rag.router import FAQRouter

faq_path = os.getenv("FAQ_PATH", "data/faq.jsonl")

def test_faq_exact():
    r = FAQRouter(faq_path)
    out = r.route("¿Qué es una arepa?", ["es"])
    assert out and out["route"] == "faq"
    assert "arepa" in out["answer"].lower()