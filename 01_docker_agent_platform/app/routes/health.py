"""Health check endpoint for the API service."""
import logging

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report API status along with best-effort dependency checks.

    A container being "started" is not the same as a service being
    "ready to accept requests". This endpoint performs lightweight,
    short-timeout probes of its direct dependencies so operators can
    distinguish the two states.
    """
    dependencies: dict[str, str] = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        dependencies["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        dependencies["postgres"] = f"unreachable: {exc}"

    try:
        response = httpx.get(f"{settings.agent_service_url}/health", timeout=2.0)
        dependencies["agent"] = "ok" if response.status_code == 200 else "degraded"
    except Exception as exc:  # noqa: BLE001
        dependencies["agent"] = f"unreachable: {exc}"

    overall = "ok" if all(v == "ok" for v in dependencies.values()) else "degraded"
    return HealthResponse(status=overall, service=settings.app_name, dependencies=dependencies)
