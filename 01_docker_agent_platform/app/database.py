"""SQLAlchemy engine/session management for the API service.

The application connects to the PostgreSQL container using the Docker
Compose service name ``postgres`` (see app/config.py), never ``localhost``.
Inside a container, ``localhost`` refers to the container itself, not to
other services on the Docker network.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they do not already exist.

    docker/init.sql seeds the database at first container start; this
    function is a defensive, idempotent fallback so the application can
    also initialize its schema on its own.
    """
    from app import models  # noqa: F401  (ensures models are registered)

    Base.metadata.create_all(bind=engine)
