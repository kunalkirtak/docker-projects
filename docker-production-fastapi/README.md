# Production FastAPI Container

A small, production-oriented FastAPI service, fully containerized with Docker
and Docker Compose. This is **Project 1 of 3** in a "Phase 10: Docker"
portfolio series focused on demonstrating real containerization fundamentals
rather than a toy demo.

## Overview

The application itself is intentionally simple: a REST API for managing
"items", backed by a JSON file on disk. The point of the project isn't the
business logic — it's everything around it:

- A Dockerfile that follows production conventions (pinned base image,
  non-root user, health check, minimal layers).
- Docker Compose managing the service's build, ports, environment,
  volume, restart policy, and health check.
- Configuration entirely through environment variables, never hard-coded.
- Structured logging instead of `print()`.
- A persistent Docker volume, proven by data surviving container
  recreation.
- A deterministic pytest suite that runs with or without Docker.

Docker concepts demonstrated: images, containers, Compose, environment
variables, named volumes, container networking basics (port publishing),
health checks, and non-root containers.

## Architecture

```text
Client
  |
  v
FastAPI Application
  |
  +--------------------+
  |                    |
  v                    v
API Routes          Health Check
  |
  v
Docker Container
  |
  v
Persistent Docker Volume
```

The API process runs inside a single Docker container. Docker Compose
publishes port 8000, injects environment variables, and mounts a named
volume (`app_data`) at `/app/data` so the JSON store survives container
restarts and recreation.

## Features

- `GET /` — service info
- `GET /health` — health status, used by the container HEALTHCHECK
- `POST /items` — create an item (validated by Pydantic)
- `GET /items` — list all items
- `GET /items/{item_id}` — fetch a single item
- `DELETE /items/{item_id}` — delete an item
- Centralized error handling (404 for missing items, 422 for invalid
  payloads, no leaked stack traces on unexpected errors)
- Structured, timestamped logging to stdout
- Environment-variable-driven configuration via Pydantic Settings
- Atomic JSON persistence (write-to-temp-then-rename, so a crash mid-write
  can't corrupt the data file)

## Technologies

```text
Python 3.12
FastAPI
Pydantic / Pydantic Settings
Docker
Docker Compose
Pytest
```

## Project Structure

```text
docker-production-fastapi/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── storage.py
│   └── routes/
│       ├── __init__.py
│       ├── health.py
│       └── items.py
│
├── tests/
│   ├── __init__.py
│   └── test_api.py
│
├── data/
│   └── .gitkeep
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

## How Docker works in this project

```text
Dockerfile
    ↓
Docker Image      (docker build — a reusable, versioned snapshot)
    ↓
Container         (docker run / compose up — a running instance of the image)
    ↓
Volume             (app_data — data that outlives the container)
    ↓
Health Check       (Docker continuously probes /health)
```

- **Image**: built once from the Dockerfile; a static, shareable artifact.
- **Container**: a running instance of that image, with its own filesystem
  layer and process.
- **Volume**: storage that lives outside the container's writable layer, so
  it isn't lost when the container is removed and recreated.
- **Health check**: Docker's way of knowing the process inside the
  container is actually serving traffic, not just alive.

## Dockerfile explanation

- `FROM python:3.12-slim` — a pinned, minimal base image. Avoids
  `python:latest`, which is a moving target and bad for reproducible builds.
- `PYTHONDONTWRITEBYTECODE=1` — skips writing `.pyc` files, keeping the
  image smaller and avoiding stale bytecode.
- `PYTHONUNBUFFERED=1` — makes stdout/stderr unbuffered so logs appear
  immediately in `docker logs`, instead of being held until the buffer
  flushes.
- Dependencies are installed **before** the application code is copied in,
  so Docker's layer cache is only invalidated when `requirements.txt`
  changes — not on every code edit.
- A non-root `appuser` is created and owns `/app`; the container runs as
  that user, not root.
- `EXPOSE 8000` documents the port the app listens on.
- `HEALTHCHECK` calls `/health` every 30 seconds so Docker (and Compose)
  can mark the container `healthy`/`unhealthy`.
- The final `CMD` runs Uvicorn bound to `0.0.0.0:8000`, the standard way to
  make a containerized service reachable from outside the container.

## Volumes

```text
app_data:/app/data
```

`app_data` is a named Docker volume mounted at `/app/data` inside the
container, which is where `DATA_FILE` (`/app/data/items.json`) lives. A
container's writable layer is deleted the moment the container is removed
— without a volume, every `docker compose down` would wipe all stored
items. Because the volume is managed by Docker separately from the
container's lifecycle, data written by one container run is still there the
next time a container is started against the same volume.

## Environment Variables

Configuration is never hard-coded. `.env.example` documents every variable
the app reads (see `app/config.py`, which loads them via Pydantic
Settings):

```text
APP_NAME=Production FastAPI Container
ENVIRONMENT=production
LOG_LEVEL=INFO
DATA_FILE=/app/data/items.json
```

Copy it to a real `.env` before running:

```bash
cp .env.example .env
```

`.env` is git-ignored — real environment files should never be committed.

## Health Checks

`GET /health` returns the service status, app name, and environment. The
Dockerfile's `HEALTHCHECK` instruction calls this endpoint with `curl`
every 30 seconds. `docker compose ps` and `docker inspect` will report the
container as `healthy` once the first successful check completes, and
`unhealthy` if checks start failing — useful for orchestrators (and humans)
deciding whether a container is actually ready to receive traffic.

## Non-root user

Running a container process as root means that, if the process is ever
compromised, an attacker inherits root privileges inside the container
(and a larger attack surface if any container-breakout vulnerability is
ever exploited). This Dockerfile creates a dedicated `appuser` with no
login shell, gives it ownership of `/app`, and switches to it with `USER
appuser` before the application starts — the process never runs as root.

## Local Python setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

## Docker setup

Build the image:

```bash
docker build -t docker-production-fastapi .
```

Run it:

```bash
docker run --rm \
  -p 8000:8000 \
  --env-file .env \
  docker-production-fastapi
```

## Docker Compose

Build and start:

```bash
docker compose up --build
```

Or run detached:

```bash
docker compose up -d
```

Useful commands:

```bash
docker compose ps
docker compose logs -f
docker compose down
```

`docker compose down -v` additionally removes the named volume, if you
want to reset stored data.

## API usage

```bash
# Root
curl http://localhost:8000/

# Health check
curl http://localhost:8000/health

# Create an item
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "First Item", "description": "An example item"}'

# List items
curl http://localhost:8000/items

# Get a single item
curl http://localhost:8000/items/<item_id>

# Delete an item
curl -X DELETE http://localhost:8000/items/<item_id>
```

## Swagger

Interactive API docs are auto-generated by FastAPI and available at:

```text
http://localhost:8000/docs
```

## Testing

```bash
pytest
```

Tests use FastAPI's `TestClient` against an isolated, per-test JSON file
(via `tmp_path`), so they're deterministic, don't touch the real data file,
and don't require Docker to run.

## Engineering Decisions

- **Slim Python image** — smaller attack surface and faster pulls than a
  full image, without missing anything this app needs.
- **Non-root user** — limits the blast radius of a compromised process.
- **Environment variables** — the same image is deployable to any
  environment; nothing environment-specific is baked in.
- **Docker volume** — separates data lifecycle from container lifecycle.
- **Health checks** — lets Docker/Compose (and any orchestrator later on)
  detect a genuinely broken instance, not just a crashed process.
- **`.dockerignore`** — keeps the build context small and prevents
  secrets, virtual environments, and dev-only files (like `.env`, `.git`,
  notebooks) from ever reaching the image.
- **Compose over a bare `docker run`** — declarative, reproducible service
  definition; also the natural place to add more services later.
- **Deterministic tests** — no reliance on ordering, external services, or
  shared state, so they're trustworthy in CI.

## Learning Outcomes

This project demonstrates the ability to:

- Write a production-style Dockerfile (pinned base image, non-root user,
  health check, efficient layer caching).
- Model a real service with Docker Compose (build, ports, environment,
  volumes, restart policy, health checks).
- Externalize configuration via environment variables using Pydantic
  Settings.
- Persist data correctly across container recreation using named volumes.
- Structure a FastAPI application with routers, schemas, and a separated
  persistence layer.
- Write deterministic, isolated automated tests for an HTTP API.
- Produce a clean `.dockerignore`/`.gitignore` split and avoid leaking
  secrets or dev artifacts into the image or the repo.

## Future Improvements

Deliberately **not** implemented here — reserved for later projects in this
series:

```text
PostgreSQL
Redis
Qdrant
Authentication
CI/CD
Observability
Multi-container architecture
```
