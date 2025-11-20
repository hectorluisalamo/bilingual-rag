import time, httpx
import redis
from api.core.config import settings
from fastapi import HTTPException

UA = settings.ua

_rds = redis.from_url(settings.redis_url) if getattr(settings, "redis_url", None) else None
TIMEOUT = httpx.Timeout(settings.http_timeout_s, read=settings.to_read, connect=settings.to_connect)

async def fetch_text(url: str, attempts: int = 3) -> httpx.Response:
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Encoding": "gzip",
        "Cache-Control": "max-age=0"
    }
    last = None

    # conditional GET (ETag / Last-Modified) via Redis
    etag_key = f"etag:{url}"
    lm_key = f"lastmod:{url}"
    if _rds:
        etag = _rds.get(etag_key)
        lm = _rds.get(lm_key)
        if etag:
            headers["If-None-Match"] = etag.decode("utf-8")
        if lm:
            headers["If-Modified-Since"] = lm.decode("utf-8")

    for i in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers, follow_redirects=True) as client:
                r = await client.get(url)
            if r.status_code == 304:  # not modified, pull from cache if store bodies later
                    # Just return empty string; caller can decide to skip re-ingest
                    return ""
            if r.status_code >= 500:
                last = f"upstream_{r.status_code}"
                time.sleep(min(2**i, 5))
                continue
            if _rds:
                if et := r.headers.get("ETag"):
                    _rds.setex(etag_key, settings.cache_ttl_s, et)
                if lm := r.headers.get("Last-Modified"):
                    _rds.setex(lm_key, settings.cache_ttl_s, lm)
            r.raise_for_status()
            return r
        except Exception as e:
            last = type(e).__name__
            time.sleep(min(2**i, 5))
    raise HTTPException(status_code=502, detail=f"fetch_failed:{last}")