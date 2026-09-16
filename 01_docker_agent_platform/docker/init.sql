-- Initial database setup for the Multi-Container AI Agent Platform.
-- Runs automatically on first container start via the PostgreSQL
-- docker-entrypoint-initdb.d mechanism. The application itself is also
-- capable of creating this table on startup (see app/database.py), so
-- this script intentionally uses IF NOT EXISTS and stays minimal.

CREATE TABLE IF NOT EXISTS tasks (
    task_id    VARCHAR(64) PRIMARY KEY,
    query      TEXT NOT NULL,
    status     VARCHAR(32) NOT NULL DEFAULT 'pending',
    result     JSONB,
    error      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS worker_jobs (
    task_id      VARCHAR(64) PRIMARY KEY,
    status       VARCHAR(32) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL
);
