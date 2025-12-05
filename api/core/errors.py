from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging, time, uuid

log = logging.getLogger("api.errors")

def json_error(code: str, message: str, context: dict | None = None, status: int = 400):
    return JSONResponse(
        status_code=status,
        content={
            "code": code,
            "message": message,
            "context": context or {}
        }
    )

class EnforceJSONMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        t0 = time.time()
        try:
            resp = await call_next(request)
            return resp
        except Exception as exc:
            etype = type(exc).__name__
            msg = str(exc)
            log.exception("unhandled", extra={"request_id": request.state.request_id})
            return JSONResponse(
                status_code=500,
                content={
                    "code": "internal_error",
                    "etype": etype,
                    "msg": msg[:500],
                    "request_id": request.state.request_id
                }
            )
        finally:
            request.state.duration_ms = int((time.time() - t0) * 1000)
