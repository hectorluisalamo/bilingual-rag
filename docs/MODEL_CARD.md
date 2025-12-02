# Model Card — Latino RAG Chatbot

## Summary
Bilingual RAG system that retrieves from licensed ES/EN sources (Wikipedia ES, CDC/USAGov/IRS Spanish pages) and answers with grounded citations.

## Intended Use
- Cultural/food/civics/health questions in Spanish or English (Spanglish tolerated).
- Educational and informational contexts where citations are required.

## Non-Intended Use
- Medical/legal advice beyond the cited material.
- Real-time breaking news; the corpus is static unless updated.

## Data
- Sources: `data/docs_catalog.json`, only Public Domain (US), CC BY-SA, or CC BY 3.0 IGO.
- Language: default Spanish; English allowed when Spanish is missing.
- Metadata: `lang, topic, country, version, published_at, approved`.

## Metrics
- Default index **c300o45**: R@1 0.74, R@5 0.80, p95 ~2.03s on 50-item gold set.

## Risks & Mitigations
- **Stale info** → store `version/published_at`; re-rank penalizes stale; show dates in citations.
- **Biases** → rely on neutral sources (gov/Wikipedia); encourage culturally diverse docs.
- **Hallucinations** → per-claim cite prompting (generator) + faithfulness smoke tests.
- **Language drift** → `lang_pref` filters; reranker improves cross-lingual matching.

## Ethical Considerations
- Respect source licenses; cite properly.
- Provide a “forget” button for user memory; TTL 48h by default.

## Maintenance
- Nightly backup (`scripts/db_backup.sh`).
- Health checks (`/health/ready`) and metrics (`/metrics`).
