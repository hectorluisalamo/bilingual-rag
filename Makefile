.PHONY: up down test fmt seed

up:
	docker compose up --build

down:
	docker compose down -v

fmt:
	ruff check . --fix

test:
	docker compose run --rm api pytest -q

seed:
	curl -X POST http://localhost:8000/ingest/url -H "Content-Type: application/json" \
	  -d '{"url":"https://es.wikipedia.org/wiki/Arepa","lang":"es","topic":"food","country":"VE"}'

.PHONY: test
test:
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q

.PHONY: eval
eval:
	python3 scripts/eval_retrieval.py --k_list 1,3,5 --lang es,en --use_reranker
	@echo "Wrote eval to eval_results.jsonl"
