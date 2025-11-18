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
