#!/bin/bash
# Inicialització de PostgreSQL per a Arena Cat.
# S'executa un sol cop, en la primera arrencada del contenidor (volum de dades buit).
#
# Crea:
#   - El rol d'aplicació (APP_DB_USER) amb permisos limitats: només DML sobre les
#     taules de l'esquema public, sense capacitat d'alterar l'esquema.
#   - La base de dades de tests (${POSTGRES_DB}_test).
#
# El superusuari POSTGRES_USER és el propietari de l'esquema i qui executa les
# migracions d'Alembic. El rol d'aplicació en consumeix les taules resultants.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Rol d'aplicació amb permisos limitats.
    CREATE ROLE "${APP_DB_USER}" WITH LOGIN PASSWORD '${APP_DB_PASSWORD}';

    -- Accés de connexió i ús de l'esquema, però sense crear-hi objectes.
    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${APP_DB_USER}";
    GRANT USAGE ON SCHEMA public TO "${APP_DB_USER}";

    -- DML sobre les taules i seqüències que crearà Alembic (executat com a ${POSTGRES_USER}).
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "${APP_DB_USER}";
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO "${APP_DB_USER}";
EOSQL

# La base de dades de tests: CREATE DATABASE no pot anar dins d'un bloc transaccional.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE DATABASE \"${POSTGRES_DB}_test\" OWNER \"${POSTGRES_USER}\";"
