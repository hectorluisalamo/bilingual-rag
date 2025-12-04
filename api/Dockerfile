FROM python:3.11-slim

# System deps (+ pg client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first for better caching
COPY pyproject.toml poetry.lock* requirements.txt* /app/
# Prefer requirements if exists, else build from pyproject
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    else \
      pip install "pip>=24.0" && pip install . ; \
    fi

# Copy app code
COPY api /app/api
COPY migrations /app/migrations

# Expose and run Uvicorn (Render provides $PORT)
ENV PORT=8000 \
    LOG_LEVEL=INFO \
    DEFAULT_INDEX_NAME=c300o45 \
    QUERY_TIMEOUT_SEC=8
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT}