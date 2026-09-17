"""
SQLAlchemy database engine and session management.

The API connects to PostgreSQL using the Docker Compose service name
"postgres" as the hostname (see app/config.py), not "localhost".
Inside the Compose network, Docker's embedded DNS resolves the
service name to the container's internal IP address. This is what
allows independent containers to find and talk to each other.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create all tables that do not yet exist.

    This project intentionally avoids a migration framework (e.g.
    Alembic) to keep the portfolio project small. In a production
    system, schema changes would be managed through versioned
    migrations instead of create_all().
    """
    from app import models  # noqa: F401  (ensure models are registered)

    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
