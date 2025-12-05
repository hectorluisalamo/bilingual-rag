#!/usr/bin/env python3
import argparse, json, pathlib, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx

def post_ingest(api, item, index_name, max_tokens, overlap, embedding_model, timeout):
    payload = {
        "url": item["url"],
        "lang": item.get("lang", "es"),
        "topic": item.get("topic"),
        "country": item.get("country"),
        "section": item.get("section"),
        "index_name": index_name,
        "max_tokens": max_tokens,
        "overlap": overlap,
        "embedding_model": embedding_model,
    }
    headers = {"Content-Type": "application/json"}
    
    _timeout = httpx.Timeout(timeout, connect=timeout, read=timeout, write=timeout, pool=timeout)
    last_err = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                r = client.post(f"{api}/ingest/url", headers=headers, json=payload)
            status = r.status_code
            try:
                body = r.json()
            except Exception:
                body = None
            if status == 200:
                return True, body
            
            detail = body if body is not None else {"text": r.text}
            if status >= 500 or (status == 422 and "no_chunks_made" in str(detail) and attempt == 1):
                time.sleep(min(2 ** attempt, 5))
                continue
            
            return False, {"status": status, "detail": detail}
        
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.RemoteProtocolError) as e:
            last_err = f"{type(e).__name__}: {str(e)}"
            time.sleep(min(2 ** attempt, 5))
            continue
        except Exception as e:
            # Always return tuple
            return False, {"status": "client_exception", "detail": f"{type(e).__name__}: {str(e)}"}
        
    return False, {"status": "network_error", "detail": last_err or "unknown"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000", help="Base API URL")
    ap.add_argument("--file", default="data/docs_catalog.json")
    ap.add_argument("--index_name", default="c300o45")
    ap.add_argument("--max_tokens", type=int, default=300)
    ap.add_argument("--overlap", type=int, default=45)
    ap.add_argument("--embedding_model", default=None)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--resume", action="store_true", help="Skip already-ingested ids from .ok file")
    args = ap.parse_args()

    path = pathlib.Path(args.file)
    docs = json.loads(path.read_text())
    ok_path = path.with_suffix(".ok.jsonl")
    fail_path = path.with_suffix(".fail.jsonl")

    already = set()
    if args.resume and ok_path.exists():
        for line in ok_path.read_text().splitlines():
            try:
                already.add(json.loads(line)["id"])
            except Exception:
                pass

    todo = [d for d in docs if d["id"] not in already]

    print(f"→ Seeding catalog: {path} → index={args.index_name} tokens={args.max_tokens} overlap={args.overlap}")
    print(f"→ Skipping {len(already)} already-ingested; processing {len(todo)}")

    ok_f = ok_path.open("a")
    fail_f = fail_path.open("a")

    def work(item):
        try:
            ok, data = post_ingest(args.api, item, args.index_name, args.max_tokens, 
                                   args.overlap, args.embedding_model, args.timeout)
            return item, ok, data
        except Exception as e:
            return item, False, {"status": "worker_exception", "detail": f"{type(e).__name__}: {str(e)}"}

    submitted = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(work, it) for it in todo]
        for fut in as_completed(futs):
            item, ok, data = fut.result()
            submitted += 1
            if ok:
                ok_f.write(json.dumps({"id": item["id"], "url": item["url"], "index": args.index_name, "data": data}) + "\n")
                ok_f.flush()
                print(f"[ok] {item['id']}")
            else:
                fail_f.write(json.dumps({"id": item["id"], "url": item["url"], "index": args.index_name, "error": data}) + "\n")
                fail_f.flush()
                print(f"[fail] {item['id']} -> {data}", file=sys.stderr)

    ok_f.close(); fail_f.close()
    print(f"Ingest done. ok={sum(1 for _ in open(ok_path)) if ok_path.exists() else 0} fail={sum(1 for _ in open(fail_path)) if fail_path.exists() else 0}")

if __name__ == "__main__":
    main()
