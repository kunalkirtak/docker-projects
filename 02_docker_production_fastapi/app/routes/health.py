"""Health check endpoint used by Docker's HEALTHCHECK and orchestrators."""

from fastapi import APIRouter

from app.config import get_settings
from app.schemas import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus)
def health_check() -> HealthStatus:
    settings = get_settings()
    return HealthStatus(
        status="ok",
        app_name=settings.app_name,
        environment=settings.environment,
    )
