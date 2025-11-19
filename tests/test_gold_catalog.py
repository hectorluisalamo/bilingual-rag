import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT_PATH = ROOT / "data" / "docs_catalog.json"
GOLD_PATH = ROOT / "data" / "gold_set.json"

def test_gold_ids_in_catalog():
    assert CAT_PATH.exists(), f"docs_catalog.json not found at {CAT_PATH}"
    assert GOLD_PATH.exists(), f"gold_set.json not found at {GOLD_PATH}"

    catalog = {d["id"] for d in json.loads(CAT_PATH.read_text())}
    gold = json.loads(GOLD_PATH.read_text())

    missing = {rid for row in gold for rid in row["relevant_ids"] if rid not in catalog}
    assert not missing, f"Missing IDs in catalog: {sorted(missing)}"
