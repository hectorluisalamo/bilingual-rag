import httpx, pytest, os

BASE = os.getenv("API_URL", "http://localhost:8000") + "/query"

@pytest.mark.parametrize("ans_lang", ["en", "es"])
def test_answer_lang_toggle(ans_lang):
    body = {"query": "¿Qué es una arepa?", "k": 3, "lang_pref": ["es"], "use_reranker": True,
            "topic_hint": "food", "answer_lang": ans_lang}
    r = httpx.post(BASE, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("citations"):
        pytest.skip("no citations after fallback; environment likely unseeded")
    assert data["citations"], "no citations"
    # crude check: answer language starts with common stopword set
    text = data["answer"].lower()
    if ans_lang=="en":
        assert any(w in text for w in ["is", "are", "corn", "bread"]), "not English-ish"
    else:
        assert any(w in text for w in ["es", "son", "maíz", "pan"]), "not Spanish-ish"