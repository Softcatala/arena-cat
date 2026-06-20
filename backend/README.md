# Backend d'Arena Cat

Servidor PostgreSQL, model de dades (SQLAlchemy) i migracions (Alembic) d'Arena Cat.

## Requisits

- [Docker](https://www.docker.com/) i Docker Compose
- [uv](https://docs.astral.sh/uv/)

## Posada en marxa

Des de l'arrel del repositori:

```bash
cp .env.example .env              # ajusta les contrasenyes
docker compose up -d --wait       # aixeca PostgreSQL i provisiona rols i BD
```

Des de `backend/`:

```bash
uv sync                       # instal·la les dependències
uv run alembic upgrade head   # crea l'esquema a arena_cat
```

## Estructura

```
app/
  config.py     # paràmetres de connexió (.env)
  db.py         # motor i classe base de SQLAlchemy
  models.py     # models de dades
migrations/     # migracions d'Alembic
tests/          # tests del model
```

## Bases de dades i rols

`docker compose` provisiona, a la primera arrencada:

- **arena_cat** — base de dades de l'aplicació.
- **arena_cat_test** — base de dades per als tests.
- **arena_app** — rol d'aplicació amb permisos limitats (només DML). Les migracions
  s'executen amb el superusuari.

## Tests

```bash
uv run pytest -v
```

Els tests necessiten el contenidor de PostgreSQL en marxa i corren contra
`arena_cat_test`.

## Migracions

Per evolucionar l'esquema:

1. Edita els models a `app/models.py`.
2. Amb la base de dades a `head`, genera la migració:
   ```bash
   uv run alembic revision --autogenerate -m "descripció del canvi"
   ```
3. **Revisa** el fitxer generat a `migrations/versions/`. L'autogeneració no ho
   detecta tot: els reanomenaments els veu com a esborrar + crear, i els canvis
   d'enum o de `CHECK` se li escapen. Tampoc no esborra els tipus `ENUM` quan
   esborra taules, així que afegeix-ho a mà al `downgrade` si en crees de nous.
4. Aplica la migració i comprova que es pot desfer:
   ```bash
   uv run alembic upgrade head
   uv run alembic downgrade -1   # i torna a 'upgrade head'
   ```
5. Executa els tests.

Ordres útils:

```bash
uv run alembic current         # revisió aplicada actualment
uv run alembic history         # historial de migracions
uv run alembic downgrade base  # desfà totes les migracions
```

## Eines

```bash
uv run ruff check .       # linting
uv run ruff format .      # formatat
```
