"""Deterministic agent workflow.

IMPORTANT: This module intentionally does NOT call any external LLM API.
Every "reasoning" step below is deterministic, rule-based Python logic.
This lets the full multi-container architecture (API -> Agent -> Worker ->
Postgres/Qdrant) run end-to-end without API keys, while keeping the
integration points obvious for swapping in a real LLM provider later
(see the ``# LLM INTEGRATION POINT`` comments).
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
import time
from dataclasses import dataclass, field

import httpx

from agent_service.config import get_agent_settings

logger = logging.getLogger(__name__)
settings = get_agent_settings()

_STOPWORDS = {
    "a", "an", "the", "of", "for", "and", "or", "to", "in", "on", "is",
    "are", "was", "were", "be", "been", "with", "as", "at", "by", "it",
    "this", "that", "these", "those", "into", "about", "its", "their",
}


def embed_text(text: str) -> list[float]:
    """Produce a deterministic, fixed-dimensional embedding.

    This is a hashed bag-of-words embedding: each token is hashed into a
    bucket of a fixed-size vector, then the vector is L2-normalized so
    cosine similarity is meaningful. It is NOT a semantic embedding model
    like OpenAI, BGE, or Sentence-Transformers -- it exists only to
    demonstrate the retrieval architecture (vector storage + cosine
    search) without requiring a downloaded model or an external API.

    # LLM INTEGRATION POINT: replace this function's body with a call to
    # a real embedding model/provider while keeping the same signature.
    """
    dims = settings.embedding_dimensions
    vector = [0.0] * dims
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        bucket = int(digest, 16) % dims
        sign = 1.0 if int(digest, 16) % 2 == 0 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def extract_keywords(query: str, max_keywords: int = 6) -> list[str]:
    """Extract simple keywords by removing stopwords and short tokens.

    # LLM INTEGRATION POINT: replace with an LLM-based keyword/entity
    # extraction call if desired.
    """
    tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
    keywords: list[str] = []
    for token in tokens:
        if token in _STOPWORDS or len(token) < 3:
            continue
        if token not in keywords:
            keywords.append(token)
    return keywords[:max_keywords]


@dataclass
class ResearchOutput:
    keywords: list[str]
    research_points: list[str]
    retrieved_knowledge: list[str] = field(default_factory=list)


class QdrantKnowledgeStore:
    """Thin HTTP wrapper around the Qdrant REST API.

    Uses the Docker Compose service name ``qdrant`` (see
    agent_service/config.py), never ``localhost``, to reach the Qdrant
    container over the shared ``agent_network``.
    """

    def __init__(self) -> None:
        self.base_url = settings.qdrant_url
        self.collection = settings.qdrant_collection

    def ensure_collection(self) -> None:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/collections/{self.collection}")
                if resp.status_code == 200:
                    return
                client.put(
                    f"{self.base_url}/collections/{self.collection}",
                    json={
                        "vectors": {
                            "size": settings.embedding_dimensions,
                            "distance": "Cosine",
                        }
                    },
                )
        except httpx.HTTPError as exc:
            logger.warning("qdrant unavailable while ensuring collection: %s", exc)

    def seed_if_empty(self, seed_items: list[str]) -> None:
        try:
            with httpx.Client(timeout=5.0) as client:
                count_resp = client.post(
                    f"{self.base_url}/collections/{self.collection}/points/count",
                    json={"exact": True},
                )
                count_resp.raise_for_status()
                current_count = count_resp.json().get("result", {}).get("count", 0)
                if current_count > 0:
                    return

                points = [
                    {
                        "id": idx,
                        "vector": embed_text(item),
                        "payload": {"text": item},
                    }
                    for idx, item in enumerate(seed_items)
                ]
                client.put(
                    f"{self.base_url}/collections/{self.collection}/points",
                    json={"points": points},
                )
                logger.info("seeded qdrant collection with %s knowledge items", len(points))
        except httpx.HTTPError as exc:
            logger.warning("qdrant unavailable while seeding: %s", exc)

    def search(self, query_vector: list[float], top_k: int = 3) -> list[str]:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(
                    f"{self.base_url}/collections/{self.collection}/points/search",
                    json={"vector": query_vector, "limit": top_k, "with_payload": True},
                )
                resp.raise_for_status()
                results = resp.json().get("result", [])
                return [r["payload"]["text"] for r in results if r.get("payload")]
        except httpx.HTTPError as exc:
            logger.warning("qdrant search failed, continuing without retrieval: %s", exc)
            return []


_SEED_KNOWLEDGE = [
    "Docker containers package an application with its dependencies for consistent execution.",
    "Docker Compose orchestrates multiple containers and defines a shared network for them.",
    "Container-to-container communication uses Docker DNS service names, not localhost.",
    "Named volumes persist data such as database files across container recreation.",
    "Health checks distinguish a container that has started from a service that is ready.",
    "Microservice architectures separate concerns like API handling, orchestration, and background work.",
    "Vector databases like Qdrant store embeddings and support similarity search.",
    "Retry and timeout logic helps distributed services fail clearly instead of hanging.",
]


class ResearchAgent:
    """Stage 1: gather deterministic research points and optional retrieval context."""

    def __init__(self, store: QdrantKnowledgeStore | None = None) -> None:
        self.store = store or QdrantKnowledgeStore()

    def run(self, query: str) -> ResearchOutput:
        logger.info("research stage started")
        keywords = extract_keywords(query)

        self.store.ensure_collection()
        self.store.seed_if_empty(_SEED_KNOWLEDGE)

        query_vector = embed_text(query)
        retrieved = self.store.search(query_vector, top_k=3)
        logger.info("retrieval completed count=%s", len(retrieved))

        research_points = [
            f"Identified key topic: '{kw}'" for kw in keywords
        ] or ["No strong keywords identified; treating query as a general request."]

        return ResearchOutput(
            keywords=keywords,
            research_points=research_points,
            retrieved_knowledge=retrieved,
        )


@dataclass
class AnalysisOutput:
    analysis: str
    recommendations: list[str]


class AnalysisAgent:
    """Stage 2: deterministic analysis over the research output.

    # LLM INTEGRATION POINT: replace this rule-based analysis with a call
    # to an LLM, passing `research.research_points` and
    # `research.retrieved_knowledge` as context.
    """

    def run(self, query: str, research: ResearchOutput) -> AnalysisOutput:
        logger.info("analysis stage started")

        keyword_count = len(research.keywords)
        knowledge_count = len(research.retrieved_knowledge)

        if keyword_count == 0:
            depth = "general"
        elif keyword_count <= 2:
            depth = "focused"
        else:
            depth = "broad"

        analysis = (
            f"The query was classified as a '{depth}' request based on "
            f"{keyword_count} extracted keyword(s). {knowledge_count} related "
            "knowledge item(s) were retrieved from the vector store to provide "
            "additional context for this analysis."
        )

        recommendations = [
            f"Consider exploring '{kw}' in more depth." for kw in research.keywords[:3]
        ]
        if knowledge_count:
            recommendations.append(
                "Review the retrieved knowledge items for supporting architectural context."
            )
        if not recommendations:
            recommendations.append(
                "Refine the query with more specific terms for a more targeted analysis."
            )

        return AnalysisOutput(analysis=analysis, recommendations=recommendations)


class ReportAgent:
    """Stage 3: assemble the final structured report."""

    def run(self, query: str, research: ResearchOutput, analysis: AnalysisOutput) -> dict:
        logger.info("report generation started")
        summary = (
            f"Processed query '{query[:80]}' through {len(research.research_points)} "
            f"research point(s) and produced {len(analysis.recommendations)} "
            "recommendation(s)."
        )
        return {
            "summary": summary,
            "analysis": analysis.analysis,
            "recommendations": analysis.recommendations,
            "keywords": research.keywords,
            "retrieved_knowledge": research.retrieved_knowledge,
        }


class AgentOrchestrator:
    """Coordinates Research -> Analysis -> Report, and notifies the worker service."""

    def __init__(
        self,
        research_agent: ResearchAgent | None = None,
        analysis_agent: AnalysisAgent | None = None,
        report_agent: ReportAgent | None = None,
    ) -> None:
        self.research_agent = research_agent or ResearchAgent()
        self.analysis_agent = analysis_agent or AnalysisAgent()
        self.report_agent = report_agent or ReportAgent()

    def run(self, task_id: str, query: str) -> dict:
        research = self.research_agent.run(query)
        analysis = self.analysis_agent.run(query, research)
        report = self.report_agent.run(query, research, analysis)

        self._notify_worker(task_id, report)
        return report

    def _notify_worker(self, task_id: str, report: dict) -> None:
        """Best-effort notification to the worker service to demonstrate
        agent -> worker container-to-container communication. Failures here
        do not fail the overall agent run; they are logged clearly.
        """
        url = f"{settings.worker_service_url}/process"
        payload = {"task_id": task_id, "report": report}

        last_error: Exception | None = None
        for attempt in range(1, settings.request_max_retries + 1):
            try:
                with httpx.Client(timeout=settings.request_timeout_seconds) as client:
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                logger.info("worker request completed task_id=%s", task_id)
                return
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "worker request failed task_id=%s attempt=%s error=%s",
                    task_id,
                    attempt,
                    exc,
                )
                if attempt < settings.request_max_retries:
                    time.sleep(0.3 * attempt)

        logger.error("worker unavailable for task_id=%s error=%s", task_id, last_error)
