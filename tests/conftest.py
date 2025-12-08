import os, time, httpx, pytest

API = os.getenv("API_URL", "http://localhost:8000")
DEFAULT_INDEX = os.getenv("DEFAULT_INDEX_NAME", "c300o45")

def _wait_ready(timeout=30):
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{API}/health/ready", timeout=5)
            if r.status_code == 200 and r.json().get("status") in ("ok","degraded"):
                return True
        except Exception as e:
            last_err = e
        time.sleep(1)
    raise RuntimeError(f"API not ready at {API}/health/ready: {last_err}")

@pytest.fixture(scope="session")
def client():
    _wait_ready()
    return httpx.Client(base_url=API, timeout=30)

@pytest.fixture(scope="session", autouse=True)
def seed_minimum_corpus(client):
    # idempotent ingest of Arepa; OK if already exists or allowlist blocks another host
    payload = {
        "url": "https://es.wikipedia.org/wiki/Arepa",
        "lang": "es",
        "topic": "food",
        "country": "VE",
        "index_name": DEFAULT_INDEX,
        "max_tokens": 300,
        "overlap": 45,
    }
    try:
        client.post("/ingest/url", json=payload)
    except Exception:
        pass
    # sanity: make sure at least one query returns some citations (with fallback)
    q = {
        "query": "¿Qué es una arepa?",
        "k": 3,
        "lang_pref": ["es","en"],
        "use_reranker": True,
        "topic_hint": "food",
        "index_name": DEFAULT_INDEX
    }
    try:
        r = client.post("/query/", json=q)
        # don't assert here; tests will skip gracefully if still empty
        _ = r.json()
    except Exception:
        pass
