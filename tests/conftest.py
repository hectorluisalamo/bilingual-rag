import os
import httpx
import pytest
from fastapi.testclient import TestClient

os.environ["TEST_MODE"] = "1"
os.environ.setdefault("FAQ_PATH", "data/faq.jsonl")

from api.main import app  # Import app after env is set

@pytest.fixture(scope="session", autouse=True)
def seed_minimum_corpus():
    # idempotent ingest; ignore errors if already present
    payload = {
        "url": "https://es.wikipedia.org/wiki/Arepa",
        "lang": "es",
        "topic": "food",
        "country": "VE",
        "index_name": os.getenv("DEFAULT_INDEX_NAME", "c300o45"),
        "max_tokens": 300,
        "overlap": 45
    }
    try:
        with httpx.Client(timeout=30) as c:
            c.post("https://latino-rag-api.onrender.com/ingest/url", json=payload)
    except Exception:
        pass
    yield