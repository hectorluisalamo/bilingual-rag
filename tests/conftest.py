import os
import pytest
from fastapi.testclient import TestClient

os.environ["TEST_MODE"] = "1"
os.environ.setdefault("FAQ_PATH", "data/faq.jsonl")

from api.main import app  # Import app after env is set

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
