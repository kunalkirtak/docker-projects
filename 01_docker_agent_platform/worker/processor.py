"""Lightweight background-style processor for the worker service.

Demonstrates a separate container receiving completed agent reports and
persisting a processing record, without introducing a message broker
(Celery/Redis/Kafka). The agent service calls this worker synchronously
over HTTP using the Docker Compose service name ``worker``; the endpoint
itself simulates a short "processing" step to represent asynchronous work.
"""
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from worker.config import get_worker_settings

logger = logging.getLogger(__name__)
settings = get_worker_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS worker_jobs (
    task_id VARCHAR(64) PRIMARY KEY,
    status VARCHAR(32) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL
)
"""


def ensure_table() -> None:
    with engine.begin() as conn:
        conn.execute(text(_CREATE_TABLE_SQL))


def process_report(task_id: str, report: dict) -> dict:
    """Simulate background processing of an agent report.

    Records a completion row in PostgreSQL (reached via the ``postgres``
    Docker Compose service name) so the worker's own persistence path can
    be independently verified.
    """
    logger.info("processing task_id=%s", task_id)
    time.sleep(0.1)  # simulate lightweight background work

    ensure_table()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO worker_jobs (task_id, status, processed_at) "
                "VALUES (:task_id, :status, :processed_at) "
                "ON CONFLICT (task_id) DO UPDATE SET "
                "status = EXCLUDED.status, processed_at = EXCLUDED.processed_at"
            ),
            {
                "task_id": task_id,
                "status": "completed",
                "processed_at": datetime.now(timezone.utc),
            },
        )

    logger.info("result generated task_id=%s", task_id)
    return {"task_id": task_id, "status": "completed", "recommendations": report.get("recommendations", [])}
