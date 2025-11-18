import os
from pydantic import BaseModel

class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    db_url: str = os.getenv("DB_URL")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    router_faq_path: str = os.getenv("ROUTER_FAQ_PATH", "./data/samples/faq.jsonl")
    cag_max_tokens: int = int(os.getenv("CAG_MAX_TOKENS", "200000"))

settings = Settings()
