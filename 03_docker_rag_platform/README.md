# Containerized RAG Platform

A multi-container backend that demonstrates how the infrastructure
behind a real Retrieval-Augmented Generation (RAG) system is built:
a FastAPI service, a PostgreSQL metadata store, and a Qdrant vector
database, all wired together and orchestrated with Docker Compose.


## Overview

* **What it does** — stores documents, generates vector embeddings
  for them, indexes those vectors in Qdrant, and exposes semantic
  search and RAG-style context-retrieval endpoints over HTTP.
* **Why Docker** — the project runs three independent services (API,
  database, vector store) that must find each other, start in a
  sane order, persist data across restarts, and be reproducible on
  any machine. Docker Compose is the tool built for exactly that.
* **What RAG components are present** — document ingestion,
  embedding generation, vector storage, similarity search, and
  structured context assembly (the **retrieval** half of RAG). See
  [Important Limitation](#important-limitation) for what is
  intentionally *not* included.

## Architecture

```text
                         Client
                           |
                           v
                    +--------------+
                    |   FastAPI    |
                    |     API      |
                    +------+-------+
                           |
                 +---------+---------+
                 |                   |
                 v                   v
          +-------------+     +-------------+
          | PostgreSQL  |     |   Qdrant    |
          | Metadata    |     | Vector DB   |
          +-------------+     +-------------+
                 |                   |
                 +---------+---------+
                           |
                           v
                    Retrieval Layer
                           |
                           v
                     RAG Context
```

Docker Compose runs three services — `api`, `postgres`, `qdrant` —
on one internal bridge network, `rag_network`.

## Technologies

```text
Python
FastAPI
PostgreSQL
SQLAlchemy
Qdrant
Docker
Docker Compose
Pytest
```

## Features

* Document CRUD (`create`, `list`, `get`, `delete`) backed by PostgreSQL
* Deterministic local embedding generation (no external API, no model download)
* Vector indexing and cosine-similarity search via Qdrant
* Semantic search endpoint (`/documents/search`)
* RAG context-retrieval endpoint (`/documents/context`)
* Health endpoint that checks PostgreSQL and Qdrant connectivity, not just process liveness
* Docker Compose healthchecks and `depends_on: condition: service_healthy` for all three services
* Named volumes so data survives container recreation
* Environment-variable-driven configuration, no hard-coded secrets
* Unit test suite (pytest) covering embeddings and request validation

## Project Structure

```text
docker-rag-platform/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── embeddings.py
│   ├── vector_store.py
│   │
│   └── routes/
│       ├── __init__.py
│       ├── health.py
│       └── documents.py
│
├── tests/
│   ├── __init__.py
│   ├── test_embeddings.py
│   └── test_schemas.py
│
├── docker/
│   └── init.sql
|
├── screenshot/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
├── .gitignore
├── pytest.ini
└── README.md
```

## How the Architecture Works

```text
FastAPI
   |
   +--> PostgreSQL   (document metadata: id, title, content, created_at)
   |
   +--> Qdrant       (embedding vector + payload for similarity search)
```

On `POST /documents`, the API writes the document to PostgreSQL
first, then generates an embedding and writes it to Qdrant. If the
Qdrant write fails, the PostgreSQL row is rolled back — the two
stores are never allowed to silently drift out of sync.

## Docker Networking

Inside the `rag_network` Compose network, the API connects to:

```text
postgres:5432
qdrant:6333
```

**never** `localhost`. Docker Compose's embedded DNS resolves each
service name (`postgres`, `qdrant`) to that container's internal IP
address automatically — this is what lets independently-built
containers discover and talk to each other without hard-coded IPs.
`localhost` inside the `api` container would refer to the API
container itself, not the database.

## Persistent Volumes

Two named volumes back the stateful services:

```text
postgres_data   -> mounted at /var/lib/postgresql/data
qdrant_data     -> mounted at /qdrant/storage
```

Because these are **named volumes** (not container filesystems),
`docker compose down` (without `-v`) removes the containers but
**keeps** the volumes — container deletion is not the same as
database data deletion. Only `docker compose down -v` removes the
volumes and therefore the data.

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

```text
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ragdb
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpassword

QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_COLLECTION=documents

EMBEDDING_DIM=128
```

`.env` is listed in `.gitignore` and must never be committed. The
values above are also used as Compose defaults if no `.env` is
present, so the stack still runs out of the box for a portfolio demo.

## Build and Run

```bash
docker compose up --build
```

## Background Mode

```bash
docker compose up -d
```

## Status

```bash
docker compose ps
```

## Logs

```bash
docker compose logs -f
docker compose logs -f api
docker compose logs -f postgres
docker compose logs -f qdrant
```

## API Documentation

```text
http://localhost:8000/docs
```

## Qdrant Dashboard

```text
http://localhost:6333/dashboard
```

## API Examples

```bash
# Health check
curl http://localhost:8000/health

# Create a document
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"title": "What is Docker", "content": "Docker packages applications into portable containers."}'

# List documents
curl http://localhost:8000/documents

# Get a single document
curl http://localhost:8000/documents/1

# Semantic search
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "docker containers", "limit": 5}'

# RAG context retrieval
curl -X POST http://localhost:8000/documents/context \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Docker?", "limit": 3}'

# Delete a document
curl -X DELETE http://localhost:8000/documents/1
```

## Example RAG Flow

```text
Document
   |
   v
PostgreSQL
   |
   +--> Embedding
           |
           v
         Qdrant
           |
           v
        Retrieval
           |
           v
      RAG Context
```

## Important Limitation

**This project implements the retrieval/context stage of RAG. It
does not use an external LLM to generate final natural-language
answers.** `/documents/context` returns the top-K most relevant
documents as structured JSON — that is where this project stops.

A production system would add a generation stage on top:

```text
Retriever
   |
   v
LLM
   |
   v
Generated Answer
```

That step is deliberately out of scope here so this project can run
completely offline, for free, with no API keys.

Similarly, the embedding function in `app/embeddings.py` is a
**deterministic, hash-based, demonstration** implementation, not a
production semantic embedding model — see the docstring in that
file for the full explanation and what it would take to swap in a
real model.

## Docker Concepts Demonstrated

* **Dockerfile** — reproducible build steps for the API image
* **Image vs. container** — a built image (`docker-rag-platform-api`) vs. a running instance of it
* **Compose** — declarative multi-service orchestration (`api`, `postgres`, `qdrant`)
* **Networking** — service-name-based DNS resolution inside `rag_network`
* **Volumes** — `postgres_data` and `qdrant_data` for durable storage
* **Health checks** — container-level (`HEALTHCHECK` / Compose `healthcheck`) vs. application-level (`GET /health`)
* **Environment variables** — all configuration injected at runtime, no hard-coded secrets
* **Service dependencies** — `depends_on: condition: service_healthy`

## Engineering Decisions

* **Deterministic local embeddings instead of a real model** — keeps
  the project runnable with zero API keys and no multi-GB model
  download, while still exercising the full vector-storage and
  retrieval pipeline honestly (see [Important Limitation](#important-limitation)).
* **PostgreSQL for metadata, Qdrant for vectors** — a realistic
  split: relational data belongs in a relational database; high-
  dimensional similarity search belongs in a purpose-built vector
  database. Keeping them separate mirrors real RAG architectures.
* **Roll back PostgreSQL writes on Qdrant failure** — prevents a
  silent split-brain where a document "exists" in one store but not
  the other.
* **`Base.metadata.create_all()` instead of Alembic migrations** —
  appropriate for a small, single-model portfolio project; a real
  production system should use versioned migrations instead.
* **Non-root user in the Dockerfile** — standard container hardening
  practice, costs nothing here.
* **No Kubernetes, Redis, Celery, or extra microservices** — this
  project's learning objective is Docker Compose fundamentals for a
  RAG stack, not a distributed-systems project. Those tools belong
  in later, dedicated portfolio projects.

## Testing

```bash
pytest
```

The test suite (`tests/test_embeddings.py`, `tests/test_schemas.py`)
covers embedding determinism, dimensionality, normalization, and
Pydantic request validation. These are **unit tests only** — they do
not require PostgreSQL or Qdrant to be running, so they pass the
same way locally, in CI, or inside Google Colab. They intentionally
do not claim to test PostgreSQL or Qdrant connectivity; verifying
that requires the full `docker compose up` stack and hitting the
live HTTP endpoints shown in [API Examples](#api-examples).

## Cleanup

```bash
docker compose down
```

Stops and removes the containers and network, but **keeps** the
named volumes (`postgres_data`, `qdrant_data`) — your data is safe.

```bash
docker compose down -v
```

Also removes the named volumes — this **permanently deletes** all
stored documents and vectors.

## Troubleshooting

| Problem | What to check |
|---|---|
| Port already in use | Another process is bound to 8000, 5432, or 6333. Stop it or change the host-side port mapping in `docker-compose.yml`. |
| Database not ready | PostgreSQL takes a few seconds to accept connections on first boot. The `api` service waits for `postgres`'s healthcheck via `depends_on`, but check `docker compose logs postgres` if it stalls. |
| Qdrant unavailable | Check `docker compose logs qdrant` and confirm port 6333 is reachable; `GET /health` reports Qdrant status directly. |
| Container logs | `docker compose logs <service>` (or `-f` to follow). |
| Rebuilding images | `docker compose up --build` after changing `Dockerfile`, `requirements.txt`, or application code. |

Useful commands:

```bash
docker compose ps
docker compose logs api
docker compose logs postgres
docker compose logs qdrant
docker compose restart
docker compose down
docker compose up --build
```

## Learning Outcomes

This project demonstrates the ability to:

* Design and containerize a multi-service backend, not just a single API process
* Wire services together through Docker Compose networking and service discovery, without hard-coded IPs
* Persist stateful services (a relational database and a vector database) across container restarts using named volumes
* Distinguish container-level health from application-level readiness, and encode that distinction in both `HEALTHCHECK` and `depends_on`
* Integrate a vector database into a real ingestion → embed → index → retrieve pipeline
* Write an honest README that documents scope and limitations rather than overstating what the system does

## Future Improvements

```text
real embedding model
LLM generation
document chunking
hybrid search
reranking
authentication
Redis
background workers
observability
CI/CD
Kubernetes
```

These are explicitly **not** implemented here to keep this project
focused on Docker Compose fundamentals for a RAG stack.
