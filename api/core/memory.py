import json, time, os
import redis
from api.core.config import settings

TTL_SECS = int(os.getenv("MEMORY_TTL_SECS", "172800"))  # 48h
MAX_ITEMS = int(os.getenv("MEMORY_MAX_ITEMS", "12"))

_rds = redis.from_url(settings.redis_url) if settings.redis_url else None

def _key(user_id: str) -> str:
    return f"mem:{user_id}"

def remember(user_id: str, item: dict):
    if not _rds:
        return
    key = _key(user_id)
    item["ts"] = time.time()
    pipe = _rds.pipeline()
    pipe.lpush(key, json.dumps(item))
    pipe.ltrim(key, 0, MAX_ITEMS - 1)
    pipe.expire(key, TTL_SECS)
    pipe.execute()

def recall(user_id: str) -> list[dict]:
    if not _rds:
        return []
    vals = _rds.lrange(_key(user_id), 0, MAX_ITEMS - 1) or []
    return [json.loads(v) for v in vals]

def forget(user_id: str):
    if _rds:
        _rds.delete(_key(user_id))
