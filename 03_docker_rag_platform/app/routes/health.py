"""Health check route.

This endpoint reports application-level health, distinct from the
container-level checks Docker Compose performs. A container can be
"started" long before the process inside it is actually ready to
serve traffic correctly — this endpoint is what a real readiness
check should call, rather than relying on `depends_on` alone.
"""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.database import SessionLocal
from app.schemas import HealthResponse
from app.vector_store import is_healthy

logger = logging.getLogger("app.routes.health")

router = APIRouter(tags=["health"])


def _check_database() -> str:
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return "ok"
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database health check failed: %s", exc)
        return "unavailable"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_status = _check_database()
    vector_status = "ok" if is_healthy() else "unavailable"
    overall = "ok" if db_status == "ok" and vector_status == "ok" else "degraded"
    return HealthResponse(status=overall, database=db_status, vector_store=vector_status)
