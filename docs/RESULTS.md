# Ablations & Metrics

All numbers from `scripts/eval_retrieval.py` on 50-item bilingual/Spanglish gold set, reranker ON.

| Variant  | Chunk | Overlap | Embed | R@1 | R@3 | R@5 | p50 ms | p95 ms | Notes |
|--------- |-----:|--------:|------|----:|----:|----:|------:|------:|------|
| default  | 600  | 60      | e3-small | 0.52 | 0.70 | 0.76 | 1324 | 2280 | Baseline |
| **c300o45** | 300 | 45     | e3-small | **0.74** | 0.80 | 0.80 | 1332 | 2030 | **Default (production-lite)** |
| c300     | 300  | 30      | e3-small | 0.66 | 0.74 | 0.74 | 1345 | 1583 | Better R@1 than baseline |
| c900     | 900  | 90      | e3-small | 0.38 | 0.66 | **0.84** | **568** | 1537 | Deeper recall; faster p50 |

Interpretation:
- We optimize for answer quality with fewer chunks → pick **c300o45** (best R@1, solid R@5).
- Keep **c900** available when stuffing more chunks is desired (breadth > precision).
