"""FastAPI entrypoint — see docs/02-architecture.md."""
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import root_router, router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="Growtrics Chemistry Video Service", version="1.0.0")
    app.include_router(root_router)
    app.include_router(router, prefix="/api/v1")

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError):
        return JSONResponse(status_code=400, content={"code": "INVALID_REQUEST", "message": str(exc)[:300]})

    @app.exception_handler(Exception)
    async def _internal(_: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            raise exc
        return JSONResponse(status_code=500, content={"code": "INTERNAL", "message": "internal error"})

    Path(settings.artifact_dir).mkdir(parents=True, exist_ok=True)
    return app


app = create_app()
