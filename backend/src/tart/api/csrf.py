"""CSRF protection of the API (ADR 0005): with the `SameSite=Lax` session cookie,
a state-changing request must carry the custom header and must not come from a
foreign `Origin`. A cross-site page cannot set a custom header without a CORS
preflight, which the API never grants.
"""

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

HEADER = "X-TART-Request"
"""Its value does not matter; the frontend sends `1`."""
REFUSED = "csrf_refused"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _origin(url: str) -> str:
    scheme, _, rest = url.partition("://")
    return f"{scheme}://{rest.split('/', 1)[0]}"


async def check(request: Request, call_next: RequestResponseEndpoint) -> Response:
    if request.method not in SAFE_METHODS and request.url.path.startswith("/api/"):
        origin = request.headers.get("Origin")
        own = _origin(str(request.app.state.configuration.environment.PUBLIC_BASE_URL))
        # Requests from the frontend's server carry no Origin; a browser's always do.
        if HEADER not in request.headers or (origin is not None and origin != own):
            return JSONResponse({"code": REFUSED}, status_code=403)
    return await call_next(request)
