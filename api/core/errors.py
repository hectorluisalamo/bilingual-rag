from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time, uuid

def json_error(code: str, message: str, context: dict | None = None, status: int = 400):
    return JSONResponse(status_code=status, content={"code": code, "message": message, "context": context or {}})

class EnforceJSONMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        t0 = time.time()
        try:
            resp = await call_next(request)
        except Exception as e:
            return json_error("internal_error", type(e).__name__, status=500)
        finally:
            d_ms = int((time.time() - t0) * 1000)
            request.state.duration_ms = d_ms
        return resp
