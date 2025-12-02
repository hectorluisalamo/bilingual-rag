# Case Study — Latino RAG: Beyond Basic RAG

## Problem
Spanish-first users ask culture/civics/health questions and want grounded answers. Many RAG demos ignore language, freshness, and routing—leading to slow, wrong, or over-engineered systems.

## Design
Pipeline: **Router (FAQ/BM25) → Retriever (vector + lang/topic filters) → Re-ranker (cross-encoder) → Generator (per-claim cites) → Guardrails**.
Memory: Redis (TTL 48h) stores language preference and entities.
Freshness: prefer `approved=true`, `version=max`; penalize stale in re-rank; always show dates.

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
