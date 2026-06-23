# AGENTS.md

Guia per a agents de codi que treballin en aquest repositori.
Per al context del projecte, vegeu `README.md`, `projecte.md` i `pla_detallat.md`.

## Visió general

Arena Cat és una plataforma d'avaluació humana de models d'IA en català.

## Estructura

- `backend/` — codi Python: model de dades, migracions i tests. Vegeu `backend/README.md`.
- `infra/` — scripts d'inicialització de la base de dades.
- `docker-compose.yml` — PostgreSQL local.
- `simulador/` — simulador de dimensionament (web estàtica).
- `docs/` — documentació del projecte (diagrama ER, etc.).

## Posada en marxa

```bash
cp .env.example .env
docker compose up -d --wait
cd backend && uv sync && uv run alembic upgrade head
```

## Ordres habituals (des de `backend/`)

- Tests: `uv run pytest` (`-v` per veure el nom de cada test)
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Migracions: vegeu `backend/README.md`

## Convencions

- **Commits**: Conventional Commits, en català (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- **Idioma**: identificadors del domini en català (taules, columnes, funcions).
- **TDD**: escriu els tests abans de la implementació sempre que es pugui.
- **Comentaris**: descriuen el codi, no la metodologia. Sense notes de procés, sense
  comparar eines, sense lligar la documentació a una issue concreta (ha de poder
  créixer amb el projecte).
- **Entorn**: gestionat amb `uv` (no cal activar venv ni pyenv). No versionis `.env`.
- **Esquema**: tot canvi a la base de dades passa per una migració d'Alembic. Revisa
  sempre els fitxers autogenerats i actualitza el diagrama a `docs/esquema_db.md`.

## Política lingüística del repository

- Els noms de les funcions, classes, etc. és l'anglès
- Els docstrings i documentació general és el català
