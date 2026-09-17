"""Pydantic models used for request/response validation."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    """Payload accepted when creating a new item."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class Item(ItemCreate):
    """Item as stored and returned by the API."""

    id: str
    created_at: datetime

    @staticmethod
    def new(payload: ItemCreate) -> "Item":
        """Build a new Item from a validated ItemCreate payload."""
        import uuid

        return Item(
            id=str(uuid.uuid4()),
            name=payload.name,
            description=payload.description,
            created_at=datetime.now(timezone.utc),
        )


class HealthStatus(BaseModel):
    """Response body for the health check endpoint."""

    status: str
    app_name: str
    environment: str
