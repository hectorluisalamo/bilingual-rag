.PHONY: up down logs seed health
up:
	docker compose up -d --build
down:
	docker compose down -v
logs:
	docker compose logs -f --tail=200
health:
	curl -s http://localhost:8000/health/ready | jq

# ---- Seeding config ----
API_URL       ?= http://localhost:8000
CATALOG_FILE  ?= data/docs_catalog.json
INDEX_NAME    ?= c300o45
TOKENS        ?= 300
OVERLAP       ?= 45
CONCURRENCY   ?= 4
# pass extra flags like: make seed SEED_FLAGS="--embedding_model text-embedding-3-small"
SEED_FLAGS    ?= --resume

.PHONY: seed reseed seed-c900

seed:
	@echo "→ Seeding catalog: $(CATALOG_FILE) → index=$(INDEX_NAME) tokens=$(TOKENS) overlap=$(OVERLAP) ($(SEED_FLAGS))"
	python3 scripts/ingest_catalog.py \
	  --api $(API_URL) \
	  --file $(CATALOG_FILE) \
	  --index_name $(INDEX_NAME) \
	  --max_tokens $(TOKENS) \
	  --overlap $(OVERLAP) \
	  --concurrency $(CONCURRENCY) \
	  $(SEED_FLAGS)

# Wipe resume logs and re-run from scratch
reseed:
	@echo "→ Clearing resume logs for $(CATALOG_FILE)"
	@rm -f $(CATALOG_FILE:.json=.ok.jsonl) $(CATALOG_FILE:.json=.fail.jsonl)
	$(MAKE) seed SEED_FLAGS=""

# Example alt index
seed-c900:
	$(MAKE) seed INDEX_NAME=c900 TOKENS=900 OVERLAP=90


.PHONY: test
test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q

.PHONY: eval
eval:
	python3 scripts/eval_retrieval.py --k_list 1,3,5 --lang es,en --use_reranker
	@echo "Wrote eval to eval_results.jsonl"

.PHONY: reindex-default reindex-c300 reindex-c900 reindex-large eval-variants
# Baseline
reindex-default:
	python3 scripts/reindex_variant.py --index_name default --max_tokens 600 --overlap 60 --embedding_model text-embedding-3-small

# Smaller chunks (300/30)
reindex-c300:
	python3 scripts/reindex_variant.py --index_name c300 --max_tokens 300 --overlap 30 --embedding_model text-embedding-3-small

# 300 w/ 45 overlap
reindex-c300o45:
	python3 scripts/reindex_variant.py --index_name c300o45 --max_tokens 300 --overlap 45 --embedding_model text-embedding-3-small

# Larger chunks (900/90)
reindex-c900:
	python3 scripts/reindex_variant.py --index_name c900 --max_tokens 900 --overlap 90 --embedding_model text-embedding-3-small

# (LATER) Larger embedding model (dimension still 3072 for -large; adjust column if switching forever) \
reindex-large: \
	python3 scripts/reindex_variant.py --index_name large --max_tokens 600 --overlap 60 --embedding_model text-embedding-3-large

# Run evals for each
eval-variants:
	python3 scripts/eval_retrieval.py --index_name default --k_list 1,3,5 --use_reranker
	python3 scripts/eval_retrieval.py --index_name c300   --k_list 1,3,5 --use_reranker
	python3 scripts/eval_retrieval.py --index_name c300o45 --k_list 1,3,5 --use_reranker
	python3 scripts/eval_retrieval.py --index_name c900   --k_list 1,3,5 --use_reranker
# (LATER) python3 scripts/eval_retrieval.py --index_name large  --k_list 1,3,5 --use_reranker

.PHONY: test ci eval-deepeval

test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q

ci:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q

# Keep DeepEval/Ragas out of pytest autoload; run explicitly here later \
eval-deepeval: \
\tpython3 scripts/eval_retrieval.py --index_name $${INDEX:-c300o45} --k_list 1,3,5 --use_reranker

.PHONY: health
health:
	@echo "→ GET $(API)/health/ready"
	@curl -s -o /dev/null -w "HTTP %{http_code} (%{time_total}s)\\n" $(API)/health/ready
	@curl -s $(API)/health/ready | jq .