# Case Study — Latino RAG: Beyond Basic RAG

## Problem
Spanish-first users ask culture/civics/health questions and want grounded answers. Many RAG demos ignore language, freshness, and routing—leading to slow, wrong, or over-engineered systems.

## Design
- Pipeline: **Router (FAQ/BM25) → Retriever (vector + lang/topic filters) → Re-ranker (cross-encoder) → Generator (per-claim cites) → Guardrails**.
- Memory: Redis (TTL 48h) stores language preference and entities.
- Freshness: prefer `approved=true`, `version=max`; penalize stale in re-rank; always show dates.
- Default index: **c300o45** (300/45) for stronger R@1 with reranker.
  * Why c300o45?: We ablated chunk size/overlap. `c300o45` (300 tokens, 45 overlap) delivered **R@1 0.74** and **R@5 0.80** with stable latency, so we standardized on it for production-lite. Larger chunks (c900) improved R@5 (0.84) but weakened R@1 (0.38), which hurt chat UX. We keep those results in the appendix for future experiments.
- Retrieval fallback: if filtered retrieval returns 0, retry without topic and with `["es","en"]`.


## Metrics & Ablations
- Routing: FAQ stage cuts cost/latency on exact repeats (not shown in table; unit tests verify).
- Retrieval:
  - Baseline (600/60): R@5 0.76, p95 ~2.28s
  - **c300o45**: R@1 **0.74**, R@5 0.80, p95 ~2.03s
  - c900: R@5 **0.84**, p50 ~0.57s, but R@1 0.38
- Takeaway: Smaller chunks + modest overlap improve first-hit accuracy; larger chunks help breadth when you retrieve more.

## Ops (Deploy & Monitor)
- One-command compose (db, redis, api, ui).
- Metrics: `/metrics` exposes request counts, p50/p95, embed/db latencies.
- Logs: JSON with `request_id`, `index`, `k`.

## Incident & Fix
- **Symptom:** Spanish query returned HTML/FAFSA noise.
- **Root cause:** No relevant docs ingested + missing metadata filters.
- **Fix:** Ingest ES Wikipedia Arepa + enable `topic_hint` and reranker → immediate precision gain.

## Next 3 Improvements
1) Add re-ranker ablation (base vs large) and log true cost/lat tradeoff.
2) Implement CAG mode when corpus < context/2; measure cache hit rate and p95.
3) Freshness tests that **force** newer version to win; surface doc date in UI prominently.

### Update “Incident & Fix” with specifics

## Incident & Fix

- **DB hostname mismatch:** Local API pointed at `DB_URL=@db` (compose-only). **Fix:** use `@localhost` for local mode.
- **pgvector operator error:** `operator does not exist: vector <=> numeric[]`. **Fix:** register pgvector’s psycopg2 adapter; added fallback `CAST(:qvec AS vector)` with a safe literal builder.
- **Empty results with topic filter:** Spanish queries returned nothing due to strict `topic_hint`. **Fix:** implemented a one-hop fallback (drop topic, widen langs), and documented index/tagging requirements.
- **Under-ingested variants:** `c300o45`/`c900` looked bad until fully reindexed. **Fix:** added `index_name` plumbing end to end and reindex scripts; counts check added to docs.
