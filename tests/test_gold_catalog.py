import json

def test_gold_ids_in_catalog():
    with open("data/docs_catalog.json") as f:
        catalog = {d["id"] for d in json.load(f)}
    with open("data/gold_set.json") as f:
        gold = json.load(f)
    missing = set()
    for row in gold:
        for rid in row["relevant_ids"]:
            if rid not in catalog:
                missing.add(rid)
    assert not missing, f"Missing IDs in catalog: {sorted(missing)}"
