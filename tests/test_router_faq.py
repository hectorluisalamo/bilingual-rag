def test_faq_exact():
    from api.rag.router import FAQRouter
    r = FAQRouter("data/faq.jsonl")
    out = r.route("¿Qué es una arepa?", ["es"])
    assert out and out["route"] == "faq"
    assert "arepa" in out["answer"].lower()

def test_faq_fuzzy():
    from pathlib import Path
    from api.rag.router import FAQRouter
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "faq.jsonl"
    r = FAQRouter(str(path))
    out = r.route("Que es una arepa", ["es"])
    assert out and out["route"] == "faq"