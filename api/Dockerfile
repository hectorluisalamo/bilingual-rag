FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*

# app deps
COPY pyproject.toml poetry.lock* /app/
RUN pip install --upgrade pip && \
    pip install "poetry==1.8.3" && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main

# app code
COPY api /app/api
COPY migrations /app/migrations

# environment
ENV HOST=0.0.0.0 PORT=8000 DEFAULT_INDEX_NAME=c300o45

# simple entrypoint: apply SQL migrations, then run API
CMD bash -c '\
  until pg_isready -h $PGHOST -p $PGPORT -U $PGUSER; do echo "waiting for db"; sleep 2; done && \
  psql "postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE" -f /app/migrations/001_init.sql && \
  [ -f /app/migrations/002_index_name.sql ] && psql "postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE" -f /app/migrations/002_index_name.sql || true && \
  [ -f /app/migrations/003_ivf_lists_200.sql ] && psql "postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE" -f /app/migrations/003_ivf_lists_200.sql || true && \
  [ -f /app/migrations/004_retention.sql ] && psql "postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE" -f /app/migrations/004_retention.sql || true && \
  uvicorn api.main:app --host $HOST --port $PORT \
'
