"""FastAPI application entrypoint."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routes import health, items
from app.storage import ItemStore


def configure_logging(log_level: str) -> None:
    """Configure structured, timestamped logging to stdout.

    Logging to stdout (not files) is deliberate: in a containerized
    deployment the container runtime is the one place logs should go, so
    they can be collected uniformly regardless of what's running inside.
    """
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = ItemStore(settings.data_file)
    logger.info(
        "Application started | environment=%s | data_file=%s",
        settings.environment,
        settings.data_file,
    )
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Production-oriented FastAPI service demonstrating Docker fundamentals.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak internal stack traces to API clients."""
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.include_router(health.router)
app.include_router(items.router)


@app.get("/", tags=["root"])
def root() -> dict:
    return {
        "app_name": settings.app_name,
        "environment": settings.environment,
        "docs": "/docs",
        "health": "/health",
    }
