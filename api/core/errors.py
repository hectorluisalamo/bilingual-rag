from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging, time, uuid, traceback

log = logging.getLogger("api.errors")

def json_error(code: str, message: str, context: dict | None = None, status: int = 400):
    return JSONResponse(status_code=status, content={"code": code, "message": message, "context": context or {}})

class EnforceJSONMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        t0 = time.time()
        try:
            resp = await call_next(request)
            return resp
        except Exception:
            # Let FastAPI handle the exception (status code, etc)
            raise
        except Exception as exc:
            # Log full traceback
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
