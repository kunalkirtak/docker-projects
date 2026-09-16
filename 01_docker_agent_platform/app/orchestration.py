"""Client responsible for talking to the agent service over HTTP.

The API service does NOT implement agent logic itself; it delegates to the
``agent`` container, reached via its Docker Compose service name
(``AGENT_SERVICE_HOST``), never ``localhost``. This module adds a small,
explicit retry/timeout layer so failures are visible and logged rather than
silent.
"""
import logging
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentServiceError(RuntimeError):
    """Raised when the agent service cannot fulfil a request after retries."""


def run_agent_workflow(task_id: str, query: str) -> dict:
    """Send a task to the agent service and return its structured result.

    Retries a fixed number of times with a short linear backoff. Any
    persistent failure is surfaced as an ``AgentServiceError`` with a clear
    message rather than being swallowed.
    """
    url = f"{settings.agent_service_url}/run"
    payload = {"task_id": task_id, "query": query}

    last_exception: Exception | None = None
    for attempt in range(1, settings.request_max_retries + 1):
        try:
            logger.info("agent request started task_id=%s attempt=%s", task_id, attempt)
            with httpx.Client(timeout=settings.request_timeout_seconds) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            logger.info("agent request completed task_id=%s", task_id)
            return data
        except (httpx.HTTPError, ValueError) as exc:  # noqa: PERF203
            last_exception = exc
            logger.warning(
                "agent request failed task_id=%s attempt=%s error=%s",
                task_id,
                attempt,
                exc,
            )
            if attempt < settings.request_max_retries:
                time.sleep(0.5 * attempt)

    raise AgentServiceError(
        f"agent service unavailable after {settings.request_max_retries} attempts: {last_exception}"
    )
