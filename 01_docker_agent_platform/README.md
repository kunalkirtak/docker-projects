# Multi-Container AI Agent Platform

**Project 3 of a Docker portfolio series.** This project demonstrates how to
design, containerize, and connect a multi-service AI-agent backend using
Docker and Docker Compose.

> This is a production-oriented **learning/portfolio architecture**
> demonstrating multi-container AI backend deployment patterns. It is not
> a production-ready AI platform (see [Limitations](#limitations)).

## Overview

The project builds on the Docker fundamentals from earlier portfolio
projects:

- **Project 1** — containerizing a single FastAPI application.
- **Project 2** — containerizing and connecting FastAPI + PostgreSQL + Qdrant.
- **Project 3 (this project)** — designing and containerizing a
  **multi-service AI-agent backend**: an API service, an agent
  orchestration service, a worker service, PostgreSQL, and Qdrant, all
  communicating over a private Docker network.

The "agent" logic is **deterministic** (rule-based Python), not an LLM.
This keeps the entire architecture runnable end-to-end with **no external
API keys**, while making the integration points obvious for plugging in a
real LLM provider later.

## Architecture

```text
                         CLIENT
                           |
                           v
                  +----------------+
                  |   FastAPI API  |
                  |    Service     |
                  +-------+--------+
                          |
                          v
                +--------------------+
                | Agent Orchestrator |
                |      Service       |
                +----+----------+----+
                     |          |
                     v          v
             +-----------+  +-----------+
             | Research  |  |  Analysis |
             |   Agent   |  |   Agent   |
             +-----------+  +-----------+
                     |
                     v
               +------------+
               |   Worker   |
               |  Service   |
               +------+-----+
                      |
             +--------+--------+
             |                 |
             v                 v
      +-------------+    +-------------+
      | PostgreSQL  |    |   Qdrant    |
      | Agent State |    | Knowledge   |
      +-------------+    +-------------+
```

## Services

| Service    | Role                                                                 | Container port |
|------------|----------------------------------------------------------------------|-----------------|
| `api`      | Public FastAPI entrypoint. Validates requests, persists task state, delegates to `agent`. | 8000 |
| `agent`    | Orchestrates the Research → Analysis → Report workflow, queries `qdrant`, notifies `worker`. | 8001 |
| `worker`   | Receives completed reports and performs lightweight background-style processing. | 8002 |
| `postgres` | Stores task metadata and worker job records.                         | 5432 |
| `qdrant`   | Stores and searches deterministic knowledge embeddings.              | 6333 |

## Agent workflow

```text
Research → Analysis → Report
```

1. **ResearchAgent** — extracts keywords from the query and retrieves
   related knowledge from Qdrant using a deterministic embedding.
2. **AnalysisAgent** — classifies the query and generates recommendations
   from the research output, using rule-based logic.
3. **ReportAgent** — assembles the final structured result.

This project intentionally uses deterministic agent logic so the complete
multi-container architecture can run without external AI API keys. A
production implementation could replace the deterministic reasoning layer
with an LLM provider. Each integration point is marked in
`agent_service/agents.py` with a `# LLM INTEGRATION POINT` comment.

The Qdrant retrieval step uses a **hashed bag-of-words embedding**
(fixed-dimensional, L2-normalized, cosine similarity) purely to
demonstrate the retrieval architecture. It is **not** equivalent to a
real embedding model such as OpenAI's, BGE, or Sentence-Transformers.

## Docker concepts demonstrated

- **Dockerfiles** — one per service (`Dockerfile.api`, `Dockerfile.agent`,
  `Dockerfile.worker`), each building a minimal, non-root image.
- **Images & containers** — each service builds its own image and runs as
  an independent container.
- **Docker Compose** — a single `docker-compose.yml` defines and wires up
  all five services.
- **Networking & service discovery** — all services share the
  `agent_network` bridge network and address each other by Compose
  service name (Docker's built-in DNS).
- **Environment variables** — all configuration (hosts, ports, credentials)
  is externalized via environment variables and `.env.example`.
- **Named volumes** — `postgres_data` and `qdrant_data` persist data
  across container recreation.
- **Health checks** — each service defines a health check, and
  `depends_on` uses `condition: service_healthy` where it matters.
- **Dependency management** — `depends_on` conditions control startup
  order without pretending a healthy dependency guarantees every future
  request will succeed (see below).
- **Non-root containers** — every application image creates and switches
  to a dedicated `appuser`.
- **Container-to-container communication** — `api → agent`,
  `agent → qdrant`, `agent → worker`, `worker → postgres`, all over
  Compose service names.

## Why `localhost` does not work

Inside a container, `localhost` (or `127.0.0.1`) refers to **that
container itself**, not to other containers in the Compose project. Each
service runs in its own network namespace. To reach another service, code
must use that service's **Docker Compose service name** — `postgres`,
`qdrant`, `agent`, `worker` — which Docker's embedded DNS resolves to the
correct container IP on the shared `agent_network`. This is why every
config value in this project (`POSTGRES_HOST`, `QDRANT_HOST`,
`AGENT_SERVICE_HOST`, `WORKER_SERVICE_HOST`) defaults to a service name,
never `localhost`.

## Project structure

```text
docker-agent-platform/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── database.py
│   ├── models.py
│   ├── orchestration.py
│   └── routes/
│       ├── __init__.py
│       ├── health.py
│       └── tasks.py
│
├── agent_service/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── agents.py
│   └── schemas.py
│
├── worker/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   └── processor.py
│
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   └── test_api.py
│
├── docker/
│   └── init.sql
│
├── Dockerfile.api
├── Dockerfile.agent
├── Dockerfile.worker
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
├── .gitignore
├── pytest.ini
└── README.md
```

## Requirements

- Docker
- Docker Compose (v2, i.e. the `docker compose` subcommand)
- Git

## Running the project

```bash
cp .env.example .env
docker compose build
docker compose up
```

or in one step:

```bash
docker compose up --build
```

This builds the `api`, `agent`, and `worker` images, pulls the official
`postgres` and `qdrant` images, creates the `agent_network` bridge
network and the `postgres_data` / `qdrant_data` volumes, then starts all
five containers with the dependency order defined in
`docker-compose.yml`.

## Verify containers

```bash
docker compose ps
```

Look for all five services in a healthy/running state.

## View logs

```bash
docker compose logs -f
```

Or for a single service:

```bash
docker compose logs -f agent
docker compose logs -f worker
```

## API documentation

Interactive Swagger UI:

```text
http://localhost:8000/docs
```

## Example API request

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze the importance of containerization for AI systems"}'
```

## Example response

```json
{
  "task_id": "task_1a2b3c4d5e6f",
  "status": "completed",
  "query": "Analyze the importance of containerization for AI systems",
  "result": {
    "summary": "Processed query 'Analyze the importance of containerization for AI systems' through 3 research point(s) and produced 3 recommendation(s).",
    "analysis": "The query was classified as a 'broad' request based on 3 extracted keyword(s). 2 related knowledge item(s) were retrieved from the vector store to provide additional context for this analysis.",
    "recommendations": [
      "Consider exploring 'importance' in more depth.",
      "Consider exploring 'containerization' in more depth.",
      "Review the retrieved knowledge items for supporting architectural context."
    ],
    "keywords": ["importance", "containerization", "systems"],
    "retrieved_knowledge": [
      "Docker containers package an application with its dependencies for consistent execution.",
      "Microservice architectures separate concerns like API handling, orchestration, and background work."
    ]
  },
  "error": null,
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:00:01Z"
}
```

## Qdrant

Because the `qdrant` service publishes port `6333` to the host for local
learning/debugging, its REST API and dashboard are reachable at:

```text
http://localhost:6333/dashboard
```

## Persistence

`postgres_data` and `qdrant_data` are named Docker volumes. They persist
task history, worker job records, and knowledge embeddings across
`docker compose down` / `docker compose up` cycles, because the data
lives outside the container filesystem.

## Networking

All five services join the `agent_network` bridge network defined in
`docker-compose.yml`. `postgres` and `worker` are **not** published to the
host — only containers on `agent_network` can reach them, which is why
their ports are absent from the `ports:` section for those services.
`qdrant`'s port is published only for optional local inspection, and
`api` is published because it is the platform's public entrypoint.

## Health checks

Health checks exist because **a container being "started" is not the
same as a service being "ready to accept requests."** `postgres` uses
`pg_isready`; `qdrant`, `agent`, `worker`, and `api` expose HTTP health
endpoints probed via `docker-compose.yml` health checks. `depends_on`
conditions wait for a dependency to report healthy before starting a
downstream service, but this only reflects readiness at startup time —
it does not guarantee every future request will succeed. That's why the
application layer (`app/orchestration.py`, `agent_service/agents.py`)
also implements its own timeouts and retries for service-to-service HTTP
calls.

## Testing

```bash
pip install -r requirements.txt
pytest
```

Unit tests in `tests/` do not require Docker, PostgreSQL, Qdrant, or any
external API — they test the deterministic agent pipeline directly and
the API service's request validation. Full end-to-end verification (a
real task flowing through `api → agent → qdrant/worker → postgres`)
requires `docker compose up` and is an integration-level exercise.

## Shutdown

```bash
docker compose down
```

Stops and removes containers and the network, but **keeps** named
volumes (`postgres_data`, `qdrant_data`) — your data survives.

```bash
docker compose down -v
```

Also removes named volumes. **This permanently deletes** all persisted
task history and Qdrant knowledge data. Use it only when you intentionally
want a clean slate.

## Troubleshooting

- **Docker not installed** — install Docker Desktop (or Docker Engine +
  Compose plugin on Linux) before running any `docker compose` command.
- **Port already in use** — another process is bound to `8000` or `6333`
  on the host; stop it or change the published port in
  `docker-compose.yml`.
- **Service not ready** — check `docker compose ps` for health status;
  a service can be "running" but still failing its health check while it
  finishes starting up.
- **Database connection failure** — confirm `postgres` is healthy
  (`docker compose logs postgres`) and that `POSTGRES_*` environment
  variables match between `.env` and what the containers were started
  with.
- **Qdrant connection failure** — confirm `qdrant` is healthy; the agent
  service degrades gracefully (empty retrieval) if Qdrant is unreachable,
  but logs a clear warning.
- **Agent service unavailable** — the API's `/health` endpoint reports
  agent connectivity; check `docker compose logs agent`.
- **Container logs** — `docker compose logs -f <service>` for any
  service name (`api`, `agent`, `worker`, `postgres`, `qdrant`).
- **Rebuilding images** — after changing dependencies or Dockerfiles, run
  `docker compose build --no-cache` (or `docker compose up --build`) to
  force a fresh build.

## Engineering decisions

- **Separate services** — splitting API, agent orchestration, and worker
  into independent containers demonstrates realistic service boundaries
  and container-to-container communication, rather than one monolithic
  container.
- **PostgreSQL** — a relational store is a natural fit for structured
  task metadata (status, timestamps, JSON result payloads).
- **Qdrant** — demonstrates a purpose-built vector database for
  similarity search, a common component in AI-agent backends.
- **Deterministic embeddings** — avoids requiring a downloaded model or
  external API just to demonstrate the retrieval architecture.
- **No external LLM API** — keeps the project runnable by anyone, with no
  API keys, cost, or rate limits, while still showing exactly where an
  LLM would plug in.
- **Docker Compose** — appropriate orchestration granularity for a
  five-service portfolio project; Kubernetes would be disproportionate.
- **Internal networking** — restricting `postgres` and `worker` to the
  internal network follows the principle of least exposure.

## Limitations

This project is an honest, deliberately scoped learning/portfolio
architecture. It does **not**:

- perform real LLM-based reasoning — agent logic is deterministic,
  rule-based Python;
- use a semantic embedding model — Qdrant vectors come from a simple
  hashed bag-of-words function, not a trained model;
- run on Kubernetes — it uses Docker Compose, appropriate for this scale;
- implement authentication or authorization on any endpoint;
- implement production secrets management (`.env` is a development
  convenience, not a secrets manager);
- use a distributed message broker — the worker is called synchronously
  over HTTP, not via a queue.

## Future improvements

- Plug in a real LLM provider at the marked integration points.
- Replace the hashed embedding with a transformer-based embedding model.
- Add authentication/authorization to the API service.
- Introduce an async job queue (e.g. Redis or Kafka) for the worker.
- Deploy via Kubernetes for multi-node orchestration.
- Add observability (metrics, tracing) across services.
- Adopt a production secrets manager instead of `.env` files.

## Learning outcomes

- Designed and containerized a multi-service AI-agent backend spanning
  five independent containers.
- Implemented Docker Compose networking, named volumes, health checks,
  and dependency ordering.
- Practiced container-to-container service discovery via Docker DNS
  instead of `localhost`.
- Built explicit timeout/retry handling for service-to-service HTTP
  calls instead of letting failures hang silently.
- Practiced running non-root application containers.
- Learned to scope a portfolio project honestly: clearly separating what
  the architecture demonstrates from what it does not claim to be.

---

## Uploading this project to GitHub

The generated project folder **is** the GitHub repository — the ZIP file
is only a convenient way to move it from Colab to your machine. The Colab
notebook itself is just the generation/development environment, not part
of the repository.

```bash
cd docker-agent-platform
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

Notes:

- `.env` is git-ignored and should **never** be committed.
- `.env.example` **should** be committed — it documents required
  configuration without leaking real values.
