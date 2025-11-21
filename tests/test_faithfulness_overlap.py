import httpx

def test_snippet_overlap_proxy():
    q = {"query": "¿Qué es una arepa?", "k":3, "lang_pref":["es"], "use_reranker":True, "topic_hint":"food"}
    r = httpx.post("http://localhost:8000/query/", json=q, timeout=20)
    r.raise_for_status()
    data = r.json()
    ans = data["answer"].lower()
    cites = data["citations"]
    # at least one citation snippet shares >= 20 chars after norm
    def norm(s):
        return "".join(ch for ch in s.lower() if ch.isalnum() or ch.isspace())
    ok = any(len(set(norm(ans).split()) & set(norm(c["snippet"]).split())) >= 6 for c in cites)
    assert ok, "faithfulness proxy failed; answer doesn't overlap citations"
