"""FastAPI API service entrypoint.

Responsible for accepting task requests, persisting task state in
PostgreSQL, and delegating agent reasoning to the separate ``agent``
container. This service intentionally does not implement agent logic.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import init_db
from app.routes import health, tasks

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting %s environment=%s", settings.app_name, settings.environment)
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "API service for the Multi-Container AI Agent Platform portfolio project. "
        "Delegates agent reasoning to a separate agent service."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(tasks.router)


@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "message": "Multi-Container AI Agent Platform API",
        "docs": "/docs",
    }
