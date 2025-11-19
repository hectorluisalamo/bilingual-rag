import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

def _default_db_url():
    host = os.getenv("DB_HOST", "localhost")
    return f"postgresql+psycopg2://postgres:postgres@{host}:5432/rag"

class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    db_url: str = os.getenv("DB_URL", _default_db_url())
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    router_faq_path: str = os.getenv("ROUTER_FAQ_PATH", "./data/samples/faq.jsonl")
    cag_max_tokens: int = int(os.getenv("CAG_MAX_TOKENS", "200000"))
    ua: str = os.getenv("BOT_UA", "LatinoRAGBot/0.1 (+contact: halamo24@gmail.com)")
    wiki_rps: float = float(os.getenv("WIKI_RPS", "4"))          # requests per second across wiki hosts
    wiki_concurrency: int = int(os.getenv("WIKI_CONC", "3"))     # concurrent requests across wiki hosts
    http_timeout_s: float = float(os.getenv("HTTP_TIMEOUT_S", "15"))
    obey_robots: bool = os.getenv("OBEY_ROBOTS", "true").lower() == "true"
    cache_ttl_s: int = int(os.getenv("FETCH_CACHE_TTL_S", "86400"))  # 24h

settings = Settings()
