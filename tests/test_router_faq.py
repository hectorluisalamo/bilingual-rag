def test_faq_exact():
    from api.rag.router import FAQRouter
    r = FAQRouter("data/faq.jsonl")
    out = r.route("¿Qué es una arepa?", ["es"])
    assert out and out["route"] == "faq"
    assert "arepa" in out["answer"].lower()

def test_faq_fuzzy():
    from api.rag.router import FAQRouter
    r = FAQRouter("data/faq.jsonl")
    out = r.route("Que es una arepa", ["es"])
    assert out and out["route"] == "faq"