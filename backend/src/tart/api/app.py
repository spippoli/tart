from fastapi import FastAPI
from fastapi.responses import PlainTextResponse


def create_app() -> FastAPI:
    app = FastAPI(title="TART API", openapi_url="/api/openapi.json", docs_url=None, redoc_url=None)

    @app.get("/api/health", response_class=PlainTextResponse)
    def health() -> str:
        # Liveness only; the Health module (Operations spec) adds the checks.
        return "ok"

    return app
