# ---- Runtime image ----
FROM python:3.11-slim

# System deps for psycopg2 & PDF parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev poppler-utils curl \
  && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    DEFAULT_INDEX_NAME=c300o45 \
    QUERY_TIMEOUT_SEC=8

WORKDIR /app

# Install requirements if provided, else default dependencies
COPY requirements.txt /app/requirements.txt
COPY api/requirements.txt /app/api-requirements.txt
RUN if [ -f /app/requirements.txt ]; then \
        pip install -r /app/requirements.txt ; \
    else \
        pip install fastapi "uvicorn[standard]" httpx pydantic sqlalchemy psycopg2-binary \
                    pgvector python-dotenv ; \
    fi

# Copy application code
COPY api /app/api
COPY migrations /app/migrations

# Expose port and run the application
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info", "--access-log"]
