.PHONY: up down logs seed health
up:
	docker compose up -d --build
down:
	docker compose down -v
logs:
	docker compose logs -f --tail=200
health:
	curl -s http://localhost:8000/health/ready | jq

# ===== Seeding via Python =====
.PHONY: seed seed-c300o45 seed-c900 seed-one seed-help

# Defaults (override at call time: make seed INDEX_NAME=c900)
API            ?= http://localhost:8000
INDEX_NAME     ?= c300o45
TOKENS         ?= 300
OVERLAP        ?= 45
CAT            ?= data/docs_catalog.json
LANG_DEFAULT   ?= es

# General seed: entire catalog with chosen index/params
seed:
	@echo "→ Seeding catalog: $(CAT) → index=$(INDEX_NAME) tokens=$(TOKENS) overlap=$(OVERLAP)"
	python3 scripts/ingest_catalog.py \
	  --api $(API) \
	  --file $(CAT) \
	  --index_name $(INDEX_NAME) \
	  --max_tokens $(TOKENS) \
	  --overlap $(OVERLAP) \
	  --lang_default $(LANG_DEFAULT)

# Convenience presets for your common variants
seed-c300o45:
	$(MAKE) seed INDEX_NAME=c300o45 TOKENS=300 OVERLAP=45

seed-c900:
	$(MAKE) seed INDEX_NAME=c900 TOKENS=900 OVERLAP=90

# Seed a single URL quickly (override URL=..., TOPIC=..., LANG=..., COUNTRY=...)
URL      ?= https://es.wikipedia.org/wiki/Arepa
TOPIC    ?= food
LANG     ?= es
COUNTRY  ?= VE

seed-one:
	@echo "→ Seeding one: $(URL) → index=$(INDEX_NAME) tokens=$(TOKENS) overlap=$(OVERLAP)"
	python3 scripts/ingest_catalog.py \
	  --api $(API) \
	  --index_name $(INDEX_NAME) \
	  --max_tokens $(TOKENS) \
	  --overlap $(OVERLAP) \
	  --single_url "$(URL)" \
	  --single_lang "$(LANG)" \
	  --single_topic "$(TOPIC)" \
	  --single_country "$(COUNTRY)"

seed-help:
	@echo "Variables: API=$(API) INDEX_NAME=$(INDEX_NAME) TOKENS=$(TOKENS) OVERLAP=$(OVERLAP) CAT=$(CAT) LANG_DEFAULT=$(LANG_DEFAULT)"
	@echo "Examples:"
	@echo "  make seed                          # full catalog → c300o45"
	@echo "  make seed INDEX_NAME=c900 TOKENS=900 OVERLAP=90"
	@echo "  make seed-c300o45                  # preset"
	@echo "  make seed-one URL=https://www.irs.gov/es/... TOPIC=civics COUNTRY=US"

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