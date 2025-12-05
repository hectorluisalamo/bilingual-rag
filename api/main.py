from contextlib import asynccontextmanager
from api.core.db import run_startup_migrations
from fastapi import FastAPI
from api.core.errors import json_error, EnforceJSONMiddleware
from api.routers import ingest, query, health, metrics
import logging, sys

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_startup_migrations()
    yield

app = FastAPI(lifespan=lifespan)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

app.add_middleware(EnforceJSONMiddleware)
app.add_exception_handler(Exception, json_error)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
