import pytest

@pytest.mark.parametrize("body", [
    {"query": "¿Qué es una arepa?", "k": 5, "lang_pref": ["es","en"], "use_reranker": True},
])
def test_query_schema(client, body):
    r = client.post("/query/", json=body)
    assert r.status_code == 200
    data = r.json()
    assert {"route","answer","citations","request_id"} <= data.keys()
    assert isinstance(data["citations"], list)

def test_query_limits(client):
    big = {"query": "x"*600, "k": 9}
    r = client.post("/query/", json=big)
    assert r.status_code in (400, 422)
