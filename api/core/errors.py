from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

async def json_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "type": exc.__class__.__name__}
    )

class EnforceJSONMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # only coerce if it looks like HTML on an API path
        if request.url.path.startswith("/query") and "text/html" in response.headers.get("content-type", ""):
            response.headers["content-type"] = "application/json"
        return response
