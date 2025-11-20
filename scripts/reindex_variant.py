#!/usr/bin/env python3
import json, argparse, httpx, sys, pathlib

CAT = pathlib.Path("data/docs_catalog.json")
API = "http://localhost:8000/ingest/url"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index_name", required=True)
    ap.add_argument("--max_tokens", type=int, default=600)
    ap.add_argument("--overlap", type=int, default=60)
    ap.add_argument("--embedding_model", default=None)
    ap.add_argument("--lang_default", default="es")
    args = ap.parse_args()

    docs = json.loads(CAT.read_text())
    with httpx.Client(timeout=60) as client:
        for d in docs:
            payload = {
                "url": d["url"],
                "lang": d.get("lang", args.lang_default),
                "topic": d.get("topic"),
                "country": d.get("country"),
                "index_name": args.index_name,
                "max_tokens": args.max_tokens,
                "overlap": args.overlap,
                "embedding_model": args.embedding_model
            }
            try:
                r = client.post(API, json=payload)
                r.raise_for_status()
                print(f"[ok] {d['id']} -> {args.index_name}")
            except Exception as e:
                print(f"[warn] {d['id']} -> {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
