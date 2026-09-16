"""Unit tests for the deterministic agent workflow.

These tests do not require Docker, Qdrant, or PostgreSQL. The Qdrant
knowledge store is replaced with a stub so the tests exercise the
Research -> Analysis -> Report pipeline in isolation.
"""
from agent_service.agents import (
    AgentOrchestrator,
    AnalysisAgent,
    ReportAgent,
    ResearchAgent,
    ResearchOutput,
    embed_text,
    extract_keywords,
)


class StubKnowledgeStore:
    """Replaces QdrantKnowledgeStore so tests never hit the network."""

    def ensure_collection(self) -> None:
        return None

    def seed_if_empty(self, seed_items: list[str]) -> None:
        return None

    def search(self, query_vector: list[float], top_k: int = 3) -> list[str]:
        return ["Docker Compose orchestrates multiple containers."]


def test_extract_keywords_filters_stopwords_and_short_tokens() -> None:
    keywords = extract_keywords("Analyze the importance of containerization for AI systems")
    assert "the" not in keywords
    assert "for" not in keywords
    assert "containerization" in keywords
    assert "systems" in keywords


def test_embed_text_is_deterministic_and_normalized() -> None:
    vec1 = embed_text("containerization and orchestration")
    vec2 = embed_text("containerization and orchestration")
    assert vec1 == vec2

    magnitude = sum(v * v for v in vec1) ** 0.5
    assert abs(magnitude - 1.0) < 1e-6 or magnitude == 0.0


def test_research_agent_returns_keywords_and_retrieval() -> None:
    agent = ResearchAgent(store=StubKnowledgeStore())
    output = agent.run("Analyze the importance of containerization for AI systems")

    assert len(output.keywords) > 0
    assert len(output.research_points) == len(output.keywords)
    assert output.retrieved_knowledge  # stub always returns one item


def test_analysis_agent_produces_recommendations() -> None:
    research = ResearchOutput(
        keywords=["containerization", "systems"],
        research_points=["Identified key topic: 'containerization'"],
        retrieved_knowledge=["Docker Compose orchestrates multiple containers."],
    )
    analysis = AnalysisAgent().run("query", research)

    assert analysis.analysis
    assert len(analysis.recommendations) >= 1


def test_report_agent_assembles_final_result() -> None:
    research = ResearchOutput(
        keywords=["containerization"],
        research_points=["Identified key topic: 'containerization'"],
        retrieved_knowledge=[],
    )
    analysis = AnalysisAgent().run("query", research)
    report = ReportAgent().run("query", research, analysis)

    assert set(report.keys()) == {
        "summary",
        "analysis",
        "recommendations",
        "keywords",
        "retrieved_knowledge",
    }
    assert report["keywords"] == ["containerization"]


def test_orchestrator_runs_full_pipeline_without_worker(monkeypatch) -> None:
    orchestrator = AgentOrchestrator(research_agent=ResearchAgent(store=StubKnowledgeStore()))

    # Avoid a real network call to the worker service during unit tests.
    monkeypatch.setattr(orchestrator, "_notify_worker", lambda task_id, report: None)

    report = orchestrator.run(task_id="task_test123", query="Explain container networking")

    assert report["summary"]
    assert isinstance(report["recommendations"], list)
    assert isinstance(report["keywords"], list)
