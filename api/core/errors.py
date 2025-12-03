from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging, time, uuid, json

log = logging.getLogger("api.errors")

def _to_jsonable(obj):
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)

def json_error(code: str, message: str, context: dict | None = None, status: int = 400):
    safe_ctx = {}
    if isinstance(context, dict):
        for k, v in context.items():
            if isinstance(v, Request):
                safe_ctx[k] = {"path": str(v.url), "method": v.method}
            else:
                safe_ctx[k] = _to_jsonable(v)
    return JSONResponse(status_code=status, content={"code": code, "message": message, "context": safe_ctx})

class EnforceJSONMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        t0 = time.time()
        try:
            resp = await call_next(request)
            return resp
        except HTTPException:
            # Let FastAPI handle HTTPExceptions
            raise
        except Exception as exc:
            # Log
            log.exception(f"Unhandled exception for request {request.state.request_id} {request.url.path}")
            return JSONResponse(
                status_code=500,
                content={
                    "code":"internal_error",
                    "message":type(exc).__name__,
                    "request_id":request.state.request_id
                    },
            )
        finally:
            request.state.duration_ms = int((time.time() - t0) * 1000)
