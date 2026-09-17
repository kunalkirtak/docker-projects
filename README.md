# Docker Projects

**A progressive portfolio series on containerizing AI/backend systems with Docker — from a single production-style FastAPI container, to a multi-service RAG stack, to a full multi-container AI-agent platform.**

Each project builds directly on the concepts of the one before it. None of them require an external API key, GPU, or paid service to run end to end — the point of the series is Docker architecture and engineering discipline, not model quality, so every "AI" component is a deliberately deterministic stand-in with a clearly marked integration point for a real model later.

---

## Projects

| # | Project | Services | Focus |
|---|---|---|---|
| 1 | [Production FastAPI Container](./02_docker_production_fastapi) | `api` | Single-container fundamentals: pinned base image, non-root user, health checks, named volumes, env-driven config, deterministic tests |
| 2 | [Containerized RAG Platform](./03_docker_rag_platform) | `api`, `postgres`, `qdrant` | Multi-service orchestration: relational metadata + vector search, service-name DNS, healthy dependency ordering, rollback on partial-write failure |
| 3 | [Multi-Container AI Agent Platform](./01_docker_agent_platform) | `api`, `agent`, `worker`, `postgres`, `qdrant` | Five-service backend: API/orchestration/worker split, agent workflow (Research → Analysis → Report), internal-only networking for non-public services |

> **Note on folder numbering:** the folder `01_docker_agent_platform` actually contains the *third* project in the series (the five-service agent platform), while `02_docker_production_fastapi` and `03_docker_rag_platform` are the first and second. Each project's own README states its real place in the series ("Project 1", "Project 2", "Project 3 of a Docker portfolio series"). Consider renaming the folders so directory order matches series order — see [Suggested Fix](#suggested-fix-folder-naming) below.

Every project runs with `docker compose up --build`, ships its own `.env.example`, Dockerfile(s), pytest suite, and a long-form README covering architecture, networking rationale, engineering decisions, limitations, and learning outcomes.

---

## Why This Repo Exists

Running a model locally is not the same skill as shipping it as a reliable, reproducible service. This series isolates that second skill on purpose:

- **Project 1 — one container, done properly.** A minimal FastAPI service that still gets the fundamentals right: a pinned slim base image, a non-root user, a real `HEALTHCHECK`, a named volume so data survives container recreation, and configuration that lives entirely in environment variables.
- **Project 2 — multiple containers, wired together.** Adds PostgreSQL (relational metadata) and Qdrant (vector search) as separate services on a private bridge network, communicating by Compose service name — never `localhost` — with `depends_on: condition: service_healthy` and a rollback so the two stores can't silently drift out of sync.
- **Project 3 — a real multi-service backend shape.** Splits a single API into `api` / `agent` / `worker` roles plus PostgreSQL and Qdrant, demonstrating internal-only service exposure, container-to-container HTTP calls with explicit timeouts/retries, and a marked `# LLM INTEGRATION POINT` for swapping deterministic agent logic for a real model later.

Across all three, the same discipline is enforced deliberately:

- **`localhost` never works between containers**, and every project explains why (each service is its own network namespace; Docker's embedded DNS resolves other services by their Compose service name instead).
- **A "started" container is not a "ready" container.** Every service defines a real health check, and startup ordering (`depends_on`) is treated as necessary but not sufficient — the application layer still implements its own timeouts and retries.
- **Data lifecycle is separated from container lifecycle.** Named volumes (`postgres_data`, `qdrant_data`, `app_data`) mean `docker compose down` never deletes real data; only `docker compose down -v` does, and every README says so explicitly.
- **Deterministic stand-ins instead of real models**, with the exact swap-in point documented, so every project runs offline, for free, with zero API keys — while being honest in its own README about exactly what it does *not* claim to be.

---

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI + Pydantic / Pydantic Settings
- **Datastores:** PostgreSQL (relational metadata), Qdrant (vector similarity search)
- **Containerization:** Docker, Docker Compose (v2)
- **Testing:** pytest — every project's unit tests run without Docker, PostgreSQL, or Qdrant; full end-to-end verification requires `docker compose up`
- **Patterns demonstrated throughout:** multi-service boundaries, Compose networking & service discovery, named volumes, health checks (`HEALTHCHECK` + application-level `/health`), non-root containers, `.env`-driven configuration, `.dockerignore` hygiene

---

## Repository Structure

```
docker-projects/
├── 02_docker_production_fastapi/     # Project 1: single-container FastAPI fundamentals
│   ├── app/                          # routes, schemas, storage, config
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── README.md
│
├── 03_docker_rag_platform/           # Project 2: FastAPI + PostgreSQL + Qdrant
│   ├── app/                          # embeddings, vector_store, database, routes
│   ├── docker/init.sql
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── README.md
│
├── 01_docker_agent_platform/         # Project 3: 5-service AI-agent backend
│   ├── app/                          # public API + orchestration
│   ├── agent_service/                # Research → Analysis → Report agents
│   ├── worker/                       # background-style processing
│   ├── docker/init.sql
│   ├── tests/
│   ├── Dockerfile.api / .agent / .worker
│   ├── docker-compose.yml
│   └── README.md
│
├── LICENSE                           # MIT
└── README.md                         # you are here
```

---

## Quick Start

Each project is independent — `cd` into whichever one you want and bring it up with Compose:

```bash
git clone https://github.com/kunalkirtak/docker-projects.git
cd docker-projects/02_docker_production_fastapi     # or 03_docker_rag_platform / 01_docker_agent_platform

cp .env.example .env
docker compose up --build
```

Then check `docker compose ps` for a healthy status and open the interactive API docs:

```
http://localhost:8000/docs
```

Run each project's test suite without Docker:

```bash
pip install -r requirements.txt
pytest
```

See each project's own README for its full architecture, Dockerfile walkthrough, API examples, troubleshooting table, and documented limitations:

- **[Production FastAPI Container →](./02_docker_production_fastapi/README.md)**
- **[Containerized RAG Platform →](./03_docker_rag_platform/README.md)**
- **[Multi-Container AI Agent Platform →](./01_docker_agent_platform/README.md)**

---

## Engineering Lessons Across the Series

- **Container-to-container communication is DNS, not localhost.** Every service in every project addresses its neighbors by Compose service name; `localhost` inside a container only ever refers to that container.
- **Health checks are a readiness signal, not a liveness one.** A "running" container can still be failing its health check while it finishes starting up — treating the two as the same thing is a common and costly mistake.
- **Keep stateful services' data outside the container.** Named volumes decouple "I removed a container" from "I lost my data" — a distinction every project's README makes explicit before `docker compose down -v` is ever mentioned.
- **Mark the deterministic-to-real swap point instead of hiding it.** Each project uses hashed/rule-based logic in place of a real embedding model or LLM, and each one states exactly where and how to plug the real thing in — an honest portfolio project documents its own scope, not just its features.

## Suggested Fix: Folder Naming

Right now the directory names don't match the series order stated inside each README (Project 1 lives in `02_...`, Project 2 in `03_...`, and Project 3 — the most advanced, five-service platform — is in `01_...`). Renaming the folders to line up numerically would make the repo easier to navigate top-to-bottom:

```bash
git mv 02_docker_production_fastapi 01_docker_production_fastapi
git mv 03_docker_rag_platform        02_docker_rag_platform
git mv 01_docker_agent_platform      03_docker_agent_platform
```

(Do this in a dedicated commit, and update any absolute links to the old paths.)

## Roadmap

- Swap deterministic agent logic and hashed embeddings for a real LLM provider and embedding model at the marked integration points.
- Add authentication/authorization to the public API endpoints (none of the three projects implement this by design).
- Introduce an async job queue (Redis/Kafka) for the worker service instead of synchronous HTTP calls.
- Add cross-service observability (metrics, tracing) and a production secrets manager in place of `.env` files.
- Explore Kubernetes as a fourth project once orchestration needs outgrow Docker Compose.

## License

MIT — see [LICENSE](./LICENSE).

## Author

Built by [Kunal Kirtak](https://github.com/kunalkirtak) as a portfolio series demonstrating Docker and containerized-backend engineering: multi-service architecture, networking, persistence, health checks, and honest scoping of what each project does and doesn't claim to be. Contributions and forks welcome — see Quick Start above.
