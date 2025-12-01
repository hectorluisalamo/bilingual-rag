import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    default_index_name: str = os.getenv("DEFAULT_INDEX_NAME", "c300o45")
    server_timeout_s: int = int(os.getenv("SERVER_TIMEOUT_S", "10"))
    db_url: str = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/rag")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    router_faq_path: str = os.getenv("ROUTER_FAQ_PATH", "./data/samples/faq.jsonl")
    cag_max_tokens: int = int(os.getenv("CAG_MAX_TOKENS", "200000"))
    ua: str = os.getenv("BOT_UA", "LatinoRAGBot/0.1 (+contact: halamo24@gmail.com) Python-httpx")
    wiki_rps: float = float(os.getenv("WIKI_RPS", "4"))          # requests per second across wiki hosts
    wiki_concurrency: int = int(os.getenv("WIKI_CONC", "3"))     # concurrent requests across wiki hosts
    http_timeout_s: float = float(os.getenv("HTTP_TIMEOUT_S", "15.0"))
    tout_read: float = float(os.getenv("TIMEOUT_READ", "25.0"))
    tout_connect: float = float(os.getenv("TIMEOUT_CONNECT", "5.0"))
    obey_robots: bool = os.getenv("OBEY_ROBOTS", "true").lower() == "true"
    cache_ttl_s: int = int(os.getenv("FETCH_CACHE_TTL_S", "86400"))  # 24h
    default_index_name: str = os.getenv("DEFAULT_INDEX_NAME", "c300o45")
    server_timeout_s: int = int(os.getenv("SERVER_TIMEOUT_S", "10"))
    dev_errors: bool = os.getenv("DEV_ERRORS", "0") == "1"

settings = Settings()
