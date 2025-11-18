FROM python:3.11-slim

WORKDIR /app
ENV POETRY_VERSION=1.8.3 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y build-essential libpq-dev poppler-utils && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
RUN pip install --no-cache-dir uvicorn[standard] && \
    pip install --no-cache-dir "poetry==$POETRY_VERSION" && \
    poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

COPY . /app
EXPOSE 8000
