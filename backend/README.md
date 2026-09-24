# Arena Cat backend

PostgreSQL server, data model (SQLAlchemy) and migrations (Alembic) for Arena Cat.

## Requirements

- [Docker](https://www.docker.com/) and Docker Compose
- [uv](https://docs.astral.sh/uv/)

## Getting started

From the repository root:

```bash
make setup  # create the local database and apply migrations
```

Optionally run `cd backend && uv run pre-commit install` to install the lint/format git hook.

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

## Users and authentication

Detailed documentation of user management and authentication (data model, cryptography,
auth flows, endpoints and GDPR): [docs/usuaris_autenticacio.md](../docs/usuaris_autenticacio.md).

## Databases and roles

On first startup, `docker compose` provisions:

- **arena_cat** — application database.
- **arena_cat_test** — test database, derived from `POSTGRES_DB` (`${POSTGRES_DB}_test`).
- **arena_app** — application role with limited permissions (DML only). Migrations run
  with the superuser.

## API

El backend de FastAPI exposa els següents endpoints:

### `GET /api/categories`

Retorna el catàleg públic de categories, ordenat per codi. Les dades provenen de la taula
`categories`, sincronitzada des de `data/prompts/categories.yaml`.

```json
{
  "categories": [
    {
      "code": "correccio",
      "name": "Correcció",
      "description": "Corregeix aquest text.",
      "evaluation_instructions": "- Correcció ortogràfica i gramatical.\n- Conservació del significat original.\n- Naturalitat en català.\n- Absència de canvis innecessaris."
    }
  ]
}
```

### `GET /api/qualification` i `POST /api/qualification`

Requereixen una sessió vàlida i la verificació del correu, si està activada.
El `GET` retorna les preguntes, les tres opcions i el llindar, sense solucions.
El `POST` rep `{"answers": {"q1": "B", "q2": "C", "...": "..."}}`, amb una
resposta A/B/C per pregunta, i retorna només el total d'encerts, el nombre de
preguntes, el llindar i si s'ha superat la prova. No retorna solucions ni correccions
per pregunta. Un formulari incomplet o invàlid retorna 422.

Les preguntes, les solucions i `min_correct` es llegeixen de
[`data/qualification.yaml`](../data/qualification.yaml). Amb el llindar inicial,
8 de 10 encerts acrediten l'usuari: es desa `users.qualified_at` i
`GET /api/auth/session` retorna `qualified: true` en les sessions següents.
Els intents fallits es poden repetir; un usuari ja acreditat rep 409 si torna
a lliurar la prova. No es desen respostes ni es generen vots o estadístiques.

La imatge del backend inclou el YAML. Es construeix des de l'arrel del repositori
amb `docker compose build api` o `docker build -f backend/Dockerfile .`.

### `GET /api/task`

Obté una nova tasca (un prompt amb dues respostes de models diferents) per a que un usuari l'avaluï.

Obtenir tasques, consultar-ne el progrés, ometre-les i votar requereix haver
superat la prova de competència lingüística; altrament, es retorna 403.

**Paràmetres de la URL:**
- `category_code` (string, opcional): La categoria de la tasca sol·licitada (p. ex., `correccio`).
  Sense filtre, s'aplica la [selecció aleatòria entre categories disponibles](../docs/sistema.md#selecció-i-registre-de-tasques).

L'usuari s'identifica amb la cookie de sessió per evitar repetir tasques.

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

Retorna el rànquing actual de models. Pot filtrar per una categoria específica o
agregar totes les categories.

`n_participants` compta els usuaris diferents amb almenys un vot dins l'àmbit
consultat, inclosos els empats i «cap de les dues». Cada usuari compta una sola
vegada, també al global si ha votat en diverses categories. Els vots sense
`user_id` es mantenen als recomptes de vots, però no al de participants.

**Paràmetres de la URL:**
- `category_code` (string, opcional): El codi de la categoria a consultar. Si s'omet,
  retorna el rànquing global agregant totes les categories.

**Resposta (200 OK):**
```json
{
  "category_code": "correccio",
  "status": "stable",
  "n_participants": 42,
  "n_votes_total": 390,
  "n_votes_decisive": 358,
  "n_ties": 23,
  "n_neither": 9,
  "best_model": "gemma-3-4b-it",
  "ranked_models": [
    {
      "rank": 1,
      "model": "gemma-3-4b-it",
      "bt_skill": 0.27
    },
    {
      "rank": 2,
      "model": "qwen-3.5-9b",
      "bt_skill": -0.04
    },
    {
      "rank": 3,
      "model": "salamandra-7b-instruct",
      "bt_skill": -0.23
    }
  ],
  "confidence": {
    "category_code": "correccio",
    "best_model": "gemma-3-4b-it",
    "n_prompts": 10,
    "n_decisive_votes": 358,
    "p_best_is_best": 0.97,
    "confidence_interval": {
      "lo": 0.12,
      "hi": 0.44
    },
    "is_stable": true
  }
}
```

Quan no es pot estimar la confiança, `p_best_is_best` i `confidence_interval`
són `null` i `is_stable` és `false`. Vegeu el
[criteri mínim i les limitacions](../docs/ranking_design.md#52-seguiment-del-mateix-model).

El camp `status` indica l'estat del rànquing: `insufficient_data` si
`confidence.confidence_interval` és `null`, `stable` si `confidence.is_stable`
és cert, o `provisional` si l'interval està disponible però el rànquing no és
estable. La manca de vots, una cobertura insuficient de prompts amb vots
decisius o models desconnectats en les comparacions decisives donen
`insufficient_data`, segons el criteri mínim enllaçat més amunt.

Sense vots decisius, `best_model` i `confidence.best_model` són `null` i
`ranked_models` és buit. Es conserven els recomptes de participants i vots;
la interfície mostra que encara no hi ha prou vots per calcular el rànquing.

## Tests

```bash
uv run pytest -v
```

The tests need the PostgreSQL container running and run against `arena_cat_test`.

## Migrations

Les contrasenyes es configuren amb el seu valor original a `POSTGRES_PASSWORD`,
també si contenen `@`, `%` o altres caràcters especials. SQLAlchemy construeix
la URL i l'entorn d'Alembic escapa els `%` només per a la interpolació de la
configuració, sense alterar la contrasenya que rep el motor de PostgreSQL.

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
