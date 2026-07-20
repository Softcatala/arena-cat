# Arena Cat backend

PostgreSQL server, data model (SQLAlchemy) and migrations (Alembic) for Arena Cat.

## Requirements

- [Docker](https://www.docker.com/) and Docker Compose
- [uv](https://docs.astral.sh/uv/)

## Getting started

From the repository root:

```bash
cp .env.example .env              # adjust the passwords
docker compose up -d --wait       # start PostgreSQL and provision roles and DB
```

From `backend/`:

```bash
uv sync                       # install the dependencies
uv run alembic upgrade head   # create the schema in arena_cat
uv run pre-commit install     # lint/format git hook (catches issues before CI)
```

## Structure

```text
app/
  config.py     # connection settings (.env)
  db.py         # SQLAlchemy engine and base class
  models.py     # data models
  schemas.py    # Pydantic models for API validation
  routes/       # FastAPI endpoints (task, vote, ranking)
  services/     # logic and database operations
  ranking/      # ranking module
migrations/     # Alembic migrations
tests/          # tests
```

## Data model

ER diagram of the schema: [docs/db_schema.md](../docs/db_schema.md).

## Databases and roles

On first startup, `docker compose` provisions:

- **arena_cat** — application database.
- **arena_cat_test** — test database, derived from `POSTGRES_DB` (`${POSTGRES_DB}_test`).
- **arena_app** — application role with limited permissions (DML only). Migrations run
  with the superuser.

## API

El backend de FastAPI exposa els següents endpoints:

### `GET /api/task`

Obté una nova tasca (un prompt amb dues respostes de models diferents) per a que un usuari l'avaluï.

**Paràmetres de la URL:**
- `category_code` (string, obligatori): La categoria de la tasca sol·licitada (p. ex., `correccio`).
- `session_id` (string, obligatori): L'identificador de sessió de l'usuari per evitar repetir tasques.

**Resposta (200 OK):**
```json
{
  "prompt": "El gat es blau",
  "response_a": "El gat és blau.",
  "response_b": "El gat es color blau.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```


### `POST /api/vote`

Registra el vot d'un usuari sobre una tasca prèviament demanada.

**Body (JSON):**
- `winner` (string): Quin model ha guanyat. Valors possibles: `"a"`, `"b"`, `"tie"` o `"neither"`.
- `token` (string): El JWT generat per l'endpoint `/api/task` (conté els IDs del prompt i les respostes).
 
**Resposta (200 OK):**
```json
{
  "status": "ok"
}
```


### `GET /api/ranking`

Retorna el rànquing actual de models per a una categoria específica.

**Paràmetres de la URL:**
- `category_code` (string, obligatori): El codi de la categoria a consultar.

**Resposta (200 OK):**
```json
{
  "category_code": "correccio",
  "n_votes_total": 390,
  "n_votes_decisive": 358,
  "n_ties": 23,
  "n_neither": 9,
  "models": ["gemma-3-4b-it", "qwen-3.5-9b", "salamandra-7b-instruct"],
  "best_model": "gemma-3-4b-it",
  "bt_skills": {
    "gemma-3-4b-it": 0.27,
    "qwen-3.5-9b": -0.04,
    "salamandra-7b-instruct": -0.23
  },
  "raw_pairwise": [
    {
      "model_a": "gemma-3-4b-it",
      "model_b": "qwen-3.5-9b",
      "wins_a": 40,
      "wins_b": 25,
      "ties": 5,
      "neither": 2,
      "win_rate_a": 0.615
    }
  ],
  "cycle_detected": false,
  "cycle_path": []
}
```

## Tests

```bash
uv run pytest -v
```

The tests need the PostgreSQL container running and run against `arena_cat_test`.

## Migrations

To evolve the schema:

1. Edit the models in `app/models.py`.
2. With the database at `head`, generate the migration:
   ```bash
   uv run alembic revision --autogenerate -m "description of the change"
   ```
3. **Review** the generated file in `migrations/versions/`. Autogeneration does not detect
   everything: renames show up as drop + create, and enum or `CHECK` changes are missed.
   It also does not drop `ENUM` types when dropping tables, so add that to `downgrade` by
   hand if you create new ones.
4. Apply the migration and check it can be reverted:
   ```bash
   uv run alembic upgrade head
   uv run alembic downgrade -1   # then go back to 'upgrade head'
   ```
5. Run the tests.

Useful commands:

```bash
uv run alembic current         # currently applied revision
uv run alembic history         # migration history
uv run alembic downgrade base  # undo all migrations
```

## Tooling

```bash
uv run ruff check .       # linting
uv run ruff format .      # formatting
```
