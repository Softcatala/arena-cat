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
```

## Structure

```
app/
  config.py     # connection settings (.env)
  db.py         # SQLAlchemy engine and base class
  models.py     # data models
migrations/     # Alembic migrations
tests/          # model tests
```

## Data model

ER diagram of the schema: [docs/db_schema.md](../docs/db_schema.md).

## Databases and roles

On first startup, `docker compose` provisions:

- **arena_cat** — application database.
- **arena_cat_test** — test database, derived from `POSTGRES_DB` (`${POSTGRES_DB}_test`).
- **arena_app** — application role with limited permissions (DML only). Migrations run
  with the superuser.

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
