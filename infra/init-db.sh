#!/bin/bash
# PostgreSQL initialization for Arena Cat.
# Runs once, on the first container startup (empty data volume).
#
# Creates:
#   - The application role (APP_DB_USER) with limited permissions: DML only on the
#     tables of the public schema, with no ability to alter the schema.
#   - The test database (${POSTGRES_DB}_test).
#
# The superuser POSTGRES_USER owns the schema and runs the Alembic migrations.
# The application role consumes the resulting tables.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Application role with limited permissions.
    CREATE ROLE "${APP_DB_USER}" WITH LOGIN PASSWORD '${APP_DB_PASSWORD}';

    -- Connection access and schema usage, but no creating objects in it.
    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${APP_DB_USER}";
    GRANT USAGE ON SCHEMA public TO "${APP_DB_USER}";

    -- DML on the tables and sequences Alembic will create (run as ${POSTGRES_USER}).
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "${APP_DB_USER}";
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO "${APP_DB_USER}";
EOSQL

# The test database: CREATE DATABASE cannot run inside a transaction block.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE \"${POSTGRES_DB}_test\" OWNER \"${POSTGRES_USER}\";"
