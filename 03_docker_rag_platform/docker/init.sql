-- Runs automatically the first time the postgres_data volume is
-- initialized (via /docker-entrypoint-initdb.d/, the official
-- PostgreSQL image's init-script mechanism). It does NOT run again
-- on subsequent container restarts as long as postgres_data already
-- contains a database.
--
-- The application also creates its tables itself at startup via
-- SQLAlchemy's Base.metadata.create_all() (see app/database.py),
-- so this file is kept minimal: it just guarantees the database
-- and a couple of sane defaults exist before the API connects.

-- Ensure the extension used for UUID generation is available should
-- a future migration need it (harmless no-op if unused today).
CREATE EXTENSION IF NOT EXISTS pgcrypto;
