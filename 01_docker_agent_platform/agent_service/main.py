"""Agent service entrypoint.

Responsible for agent orchestration: Research -> Analysis -> Report, with
a retrieval step against Qdrant and a notification to the worker service.
This service uses deterministic logic only -- see agent_service/agents.py
for details and LLM integration points.
"""
import logging

from fastapi import FastAPI, HTTPException

from agent_service.agents import AgentOrchestrator
from agent_service.config import get_agent_settings
from agent_service.schemas import AgentRunRequest, AgentRunResponse

settings = get_agent_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Deterministic agent orchestration service (no external LLM required).",
    version="1.0.0",
)

orchestrator = AgentOrchestrator()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.post("/run", response_model=AgentRunResponse)
def run(payload: AgentRunRequest) -> AgentRunResponse:
    try:
        report = orchestrator.run(task_id=payload.task_id, query=payload.query)
        return AgentRunResponse.model_validate(report)
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent run failed task_id=%s", payload.task_id)
        raise HTTPException(status_code=500, detail=f"agent run failed: {exc}") from exc
