FROM python:3.12-slim

# Instal·lem `uv` copiant-lo directament de la seva imatge oficial (és la manera recomanada per Astral)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Establim el directori de treball a dins del contenidor
WORKDIR /app

# Copiem només els fitxers de dependències
COPY pyproject.toml uv.lock ./

# Instal·lem les dependències
RUN uv sync --frozen --no-install-project

# Copiem la resta del codi (app/, scripts/, etc.)
COPY . .

# Exposem el port 8000
EXPOSE 8000

# Executem el servidor
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]