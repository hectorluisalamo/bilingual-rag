import httpx, pytest

BASE="http://localhost:8000"

@pytest.mark.parametrize("body", [
    {"query": "¿Qué es una arepa?", "k":5, "lang_pref":["es"]},
])
def test_query_schema(body):
    r = httpx.post(f"{BASE}/query/", json=body, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert {"route", "answer", "citations", "request_id"} <= data.keys()
    assert isinstance(data["citations"], list)

def test_query_limits():
    big = {"query":"x"*600, "k":9}
    r = httpx.post(f"{BASE}/query/", json=big, timeout=20)
    assert r.status_code in (400, 422)
