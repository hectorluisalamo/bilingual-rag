import asyncio, time, httpx, re
from urllib.parse import urlparse, quote
from urllib import robotparser
import redis
from api.core.config import settings

WIKI_HOSTS = ("wikipedia.org",)
UA = settings.ua

# Global sema & token bucket for wiki hosts
_sem = asyncio.Semaphore(settings.wiki_concurrency)
_tokens = settings.wiki_rps
_last_ts = time.monotonic()
_lock = asyncio.Lock()

_r = redis.from_url(settings.redis_url) if getattr(settings, "redis_url", None) else None
TIMEOUT = httpx.Timeout(settings.http_timeout_s, read=settings.http_timeout_s, connect=5.0)

def _is_wiki(host: str) -> bool:
    host = host.lower()
    return any(host.endswith(h) for h in WIKI_HOSTS)

def _wiki_html_url(url: str) -> str | None:
    p = urlparse(url)
    if not _is_wiki(p.netloc):
        return None
    m = re.search(r"/wiki/(.+)$", p.path)
    if not m:
        return None
    title = m.group(1)
    return f"https://{p.netloc}/api/rest_v1/page/html/{quote(title)}"

async def _throttle():
    global _tokens, _last_ts
    async with _lock:
        now = time.monotonic()
        # refill tokens
        refill = (now - _last_ts) * settings.wiki_rps
        _tokens = min(settings.wiki_rps, _tokens + refill)
        if _tokens < 1.0:
            wait_s = (1.0 - _tokens) / settings.wiki_rps
            await asyncio.sleep(wait_s)
            now = time.monotonic()
            refill = (now - _last_ts) * settings.wiki_rps
            _tokens = min(settings.wiki_rps, _tokens + refill)
        _tokens -= 1.0
        _last_ts = now

async def fetch_text(url: str, accept_lang: str = "es") -> str:
    target = _wiki_html_url(url) or url
    p = urlparse(target)
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": accept_lang,
        "Accept-Encoding": "gzip",
        "Cache-Control": "max-age=0"
    }

    # conditional GET (ETag / Last-Modified) via Redis
    etag_key = f"etag:{target}"
    lm_key = f"lastmod:{target}"
    if _r:
        etag = _r.get(etag_key)
        lm = _r.get(lm_key)
        if etag:
            headers["If-None-Match"] = etag.decode("utf-8")
        if lm:
            headers["If-Modified-Since"] = lm.decode("utf-8")

    async with _sem:
        if _is_wiki(p.netloc):
            await _throttle()
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=headers, follow_redirects=True) as client:
            attempts = 0
            while True:
                attempts += 1
                r = await client.get(target)
                if r.status_code == 304:  # not modified, pull from cache if store bodies later
                    # Just return empty string; caller can decide to skip re-ingest
                    return ""
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After")
                    try:
                        delay = float(ra) if ra else min(2 ** attempts, 30)
                    except ValueError:
                        delay = min(2 ** attempts, 30)
                    await asyncio.sleep(delay)
                    continue
                r.raise_for_status()
                if _r:
                    if et := r.headers.get("ETag"):
                        _r.setex(etag_key, settings.cache_ttl_s, et)
                    if lm := r.headers.get("Last-Modified"):
                        _r.setex(lm_key, settings.cache_ttl_s, lm)
                return r