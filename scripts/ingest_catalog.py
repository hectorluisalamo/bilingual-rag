import json, os, sys, httpx

API = os.environ.get("API", "http://localhost:8000")
CATALOG = "data/docs_catalog.json"

def main():
    with open(CATALOG) as f:
        docs = json.load(f)
    ok, fail = 0, 0
    for d in docs:
        payload = {
            "url": d["url"],
            "lang": d.get("lang","es"),
            "topic": d.get("topic"),
            "country": d.get("country")
        }
        try:
            r = httpx.post(f"{API}/ingest/url", json=payload, timeout=30)
            r.raise_for_status()
            ok += 1
        except Exception as e:
            fail += 1
            print(f"FAIL {d['id']}: {e}", file=sys.stderr)
    print(f"Ingest done. ok={ok} fail={fail}")

if __name__ == "__main__":
    main()
