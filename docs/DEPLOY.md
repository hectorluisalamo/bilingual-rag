# Deploy

## Local
cp .env.example .env   # add OPENAI_API_KEY
make up
make health            # expect {"status":"ok", ...}
open http://localhost:8501

## Seed data
make seed

## Logs
make logs

## Tear down
make down

## Remote (one-box VM)
- Install Docker & docker-compose-plugin
- Copy repo & .env (with real OPENAI_API_KEY)
- `docker compose up -d --build`
- Expose port 80/443 with a reverse proxy (Caddy or Nginx). Optional TLS.
