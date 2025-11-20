#!/usr/bin/env python3
import json, time, statistics, argparse, httpx, pathlib

API = "http://localhost:8000/query/"
CAT_PATH = pathlib.Path("data/docs_catalog.json")
GOLD_PATH = pathlib.Path("data/gold_set.json")
OUT_PATH = pathlib.Path("eval_results.jsonl")

def load_catalog():
    by_id = {}
    if CAT_PATH.exists():
        for d in json.loads(CAT_PATH.read_text()):
            by_id[d["id"]] = d
    return by_id

def eval_once(client, q, topic_hint=None, lang_pref=("es","en"), use_reranker=True, k=5):
    payload = {
        "query": q,
        "k": k,
        "lang_pref": list(lang_pref),
        "use_reranker": use_reranker,
        "topic_hint": topic_hint,
    }
    t0 = time.time()
    r = client.post(API, json=payload, timeout=30)
    dt = (time.time() - t0) * 1000.0
    r.raise_for_status()
    data = r.json()
    uris = [c["uri"] for c in data.get("citations", [])]
    return uris, dt, data

def uri_matches_relevant(uri: str, relevant_ids, catalog):
    # A doc matches if its catalog URL appears as prefix in the citation URI
    for rid in relevant_ids:
        item = catalog.get(rid)
        if not item: 
            continue
        if uri.startswith(item["url"]):
            return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k_list", default="1,3,5")
    ap.add_argument("--lang", default="es,en")
    ap.add_argument("--use_reranker", action="store_true", default=True)
    args = ap.parse_args()

    ks = [int(x) for x in args.k_list.split(",")]
    langs = tuple(args.lang.split(","))

    catalog = load_catalog()
    gold = json.loads(GOLD_PATH.read_text())

    results = {k: {"hits":0, "total":0, "latencies": []} for k in ks}
    with httpx.Client() as client, OUT_PATH.open("w") as out:
        for row in gold:
            q = row["query"]
            rel = row["relevant_ids"]
            # infer topic_hint from first relevant doc if available
            topic_hint = None
            for rid in rel:
                if rid in catalog and catalog[rid].get("topic"):
                    topic_hint = catalog[rid]["topic"]
                    break
            for k in ks:
                uris, ms, data = eval_once(client, q, topic_hint, langs, args.use_reranker, k)
                hit = any(uri_matches_relevant(u, rel, catalog) for u in uris)
                results[k]["hits"] += int(hit)
                results[k]["total"] += 1
                results[k]["latencies"].append(ms)
                out.write(json.dumps({
                    "query": q, "k": k, "hit": hit, "latency_ms": ms,
                    "topic_hint": topic_hint, "uris": uris, "relevant_ids": rel
                }) + "\n")

    summary = {}
    for k, r in results.items():
        p50 = statistics.median(r["latencies"]) if r["latencies"] else 0.0
        p95 = statistics.quantiles(r["latencies"], n=20)[18] if len(r["latencies"]) >= 20 else max(r["latencies"] or [0.0])
        recall = r["hits"] / max(r["total"], 1)
        summary[k] = {"retrieval@k": round(recall, 3), "p50_ms": int(p50), "p95_ms": int(p95), "count": r["total"]}
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
