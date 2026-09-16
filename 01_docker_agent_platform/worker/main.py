"""Worker service entrypoint.

Exposes a small internal HTTP API used by the agent service to hand off
completed reports for background-style processing. Kept intentionally
simple: no message broker, no task queue framework.
"""
import logging

from fastapi import FastAPI, HTTPException

from worker.config import get_worker_settings
from worker.processor import process_report

settings = get_worker_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Lightweight worker service demonstrating container-to-container hand-off.",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.post("/process")
def process(payload: dict) -> dict:
    task_id = payload.get("task_id")
    report = payload.get("report", {})
    if not task_id:
        raise HTTPException(status_code=422, detail="task_id is required")

    try:
        return process_report(task_id=task_id, report=report)
    except Exception as exc:  # noqa: BLE001
        logger.exception("worker processing failed task_id=%s", task_id)
        raise HTTPException(status_code=500, detail=f"worker processing failed: {exc}") from exc
