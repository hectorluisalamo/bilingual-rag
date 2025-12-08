# Ablations & Metrics

All numbers from `scripts/eval_retrieval.py` on 50-item bilingual/Spanglish gold set, reranker ON.

| Variant  | Chunk | Overlap | Embed | R@1 | R@3 | R@5 | p50 ms | p95 ms | Notes |
|--------- |-----:|--------:|------|----:|----:|----:|------:|------:|------|
| **c300o45** | 300 | 45     | e3-small | **0.74** | 0.80 | 0.80 | 1332 | 2030 | **Default (production-lite)** |
| default  | 600  | 60      | e3-small | 0.52 | 0.70 | 0.76 | 1324 | 2280 | Historical; baseline |
| c300     | 300  | 30      | e3-small | 0.66 | 0.74 | 0.74 | 1345 | 1583 | Better Historical; R@1 than baseline |
| c900     | 900  | 90      | e3-small | 0.38 | 0.66 | **0.84** | **568** | 1537 | Historical; Deeper recall, faster p50 |

Interpretation:
- We optimize for answer quality with fewer chunks → pick **c300o45** (best R@1, solid R@5).