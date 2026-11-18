FROM python:3.13-slim

# Instal·lem `uv` copiant-lo directament de la seva imatge oficial (és la manera recomanada per Astral)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Establim el directori de treball a dins del contenidor
WORKDIR /app/backend

# Copiem només els fitxers de dependències
COPY backend/pyproject.toml backend/uv.lock ./

# Instal·lem les dependències
RUN uv sync --frozen --no-install-project

# Copiem el codi, les migracions i el qüestionari
COPY backend/app/ app/
COPY backend/migrations/ migrations/
COPY backend/alembic.ini .
COPY data/qualification.yaml /app/data/qualification.yaml

# Exposem el port 8000
EXPOSE 8000

# Executem el servidor corrent primer les migracions si n'hi ha
CMD ["sh", "-c", "uv run alembic upgrade head && exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
