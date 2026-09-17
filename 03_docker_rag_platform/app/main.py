"""FastAPI application entrypoint for the Containerized RAG Platform."""

import logging

from fastapi import FastAPI

from app.database import init_db
from app.routes import documents, health
from app.vector_store import create_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

app = FastAPI(
    title="Containerized RAG Platform",
    description=(
        "A multi-container RAG backend demonstrating Docker Compose, "
        "PostgreSQL, Qdrant, and the retrieval stage of Retrieval-"
        "Augmented Generation."
    ),
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(documents.router)


@app.on_event("startup")
def on_startup() -> None:
    """Initialize PostgreSQL tables and the Qdrant collection.

    Note: a successful container start does not mean these
    dependencies are ready yet (see README "Docker Compose service
    readiness"). This is why PostgreSQL and Qdrant have healthchecks
    and the API declares `depends_on: condition: service_healthy`.
    """
    init_db()
    try:
        create_collection()
    except Exception as exc:  # noqa: BLE001
        logger.error("Could not initialize Qdrant collection at startup: %s", exc)


@app.get("/")
def root() -> dict:
    return {
        "name": "Containerized RAG Platform",
        "docs": "/docs",
        "health": "/health",
    }
