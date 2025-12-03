import httpx, urllib
from bs4 import BeautifulSoup
import redis
from api.core.config import settings
from fastapi import HTTPException

UA = settings.ua

_rds = redis.from_url(settings.redis_url) if getattr(settings, "redis_url", None) else None
TIMEOUT = httpx.Timeout(settings.http_timeout_s, read=settings.tout_read, connect=settings.tout_connect)

async def fetch_text(url: str) -> str:
    headers = {
        "User-Agent": "LatinoRAGBot/0.1 (+https://demo.local)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    # 1) Fetch HTML
    timeout = httpx.Timeout(15.0, read=25.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        r = await client.get(url)
        r.raise_for_status()
        html = r.text

    # 2) Parse with site-specific selectors
    soup = BeautifulSoup(html, "html.parser")
    host = httpx.URL(url).host or ""
    text = ""

    if "wikipedia.org" in host:
        # Prefer main content
        node = soup.select_one("#mw-content-text") or soup.find("main") or soup.find("article")
        if node:
            text = node.get_text(" ")
        # If still thin, use REST plain-text
        if len(text.strip()) < 400 and "/wiki/" in url:
            title = urllib.parse.unquote(url.split("/wiki/")[-1])
            rest = f"https://{host.replace('m.', '')}/api/rest_v1/page/plain/{title}"
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
                rr = await client.get(rest)
                if rr.status_code == 200 and rr.text.strip():
                    text = rr.text

    elif host in {"www.cdc.gov", "www.usa.gov", "www.irs.gov", "www.uscis.gov", "www.vote.gov", "www.who.int"}:
        node = soup.find("main") or soup.find(id="main") or soup.find("article")
        text = (node.get_text(" ") if node else soup.get_text(" "))

    else:
        text = soup.get_text(" ")

    # Normalize whitespace
    text = " ".join(text.split())
    return text