from __future__ import annotations
import os, json, time
from typing import Any, Dict, Optional

# Lazy import so tests without the package still run
try:
    from openai import OpenAI, APIError, RateLimitError, APITimeoutError
except Exception:
    OpenAI = None
    APIError = RateLimitError = APITimeoutError = Exception

_client = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

def _client_ok() -> bool:
    return bool(OPENAI_API_KEY) and OpenAI is not None

def _get_client():
    global _client
    if _client is None and _client_ok():
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

def openai_chat(
    system: str,
    user: str,
    *,
    model: Optional[str] = None,
    json_mode: bool = False,
    max_tokens: int = 400,
    temperature: float = 0.2,
    timeout_s: float = 8.0,
    retries: int = 1,
) -> Any:
    """
    Returns str by default; when json_mode=True returns parsed dict
    Fallback (no API key): returns echo/extracted stub so the app won't crash
    """
    use_model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not _client_ok():
        # local fallback
        if json_mode:
            return {"quotes": []}
        return user[: max_tokens]

    last_err = None
    for attempt in range(retries + 1):
        try:
            client = _get_client()
            kwargs: Dict[str, Any] = {
                "model": use_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": timeout_s,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content or ""
            if json_mode:
                try:
                    return json.loads(text)
                except Exception:
                    # if model returns invalid JSON once, try plain parse fallback
                    return json.loads(text[text.find("{"): text.rfind("}")+1])
            return text
        except (RateLimitError, APITimeoutError, APIError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"openai_chat failed: {last_err!r}")
