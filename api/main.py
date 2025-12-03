from fastapi import FastAPI
from api.core.errors import json_error, EnforceJSONMiddleware
from api.routers import ingest, query, health

app = FastAPI(title="Bilingual RAG Chatbot")

app.add_middleware(EnforceJSONMiddleware)
app.add_exception_handler(Exception, json_error)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, prefix="/query", tags=["query"])
