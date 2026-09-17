# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr.
# Unbuffered output is important in containers so logs appear in real time
# in `docker logs` instead of being held in a buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so this layer is cached and only rebuilt when
# requirements.txt actually changes, not on every source code edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# curl is needed for the HEALTHCHECK below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY app ./app

# Create a non-root user and a writable data directory owned by it.
# Running as root inside a container is unnecessary risk: if the process is
# ever compromised, a non-root user limits what it can do on the host.
RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Docker (and Compose) use this to know if the container is actually
# serving traffic, not just running. A container stuck in a bad state gets
# marked unhealthy instead of silently accepting requests it can't serve.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
