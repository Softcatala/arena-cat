# AGENTS.md

Guia per als agents de programació que treballen en aquest repositori.
Per conèixer el context del projecte, consulta `README.md`, `docs/projecte.md` i `docs/sistema.md`.

## Visió general

Arena Cat és una plataforma d'avaluació humana de models d'IA en català.

## Estructura

- `backend/` — Codi Python: model de dades, migracions i proves. Consulta `backend/README.md`.
- `frontend/` — Interfície web d'avaluació (React + Vite). Consulta `frontend/README.md`.
- `infra/` — Scripts d'inicialització de la base de dades.
- `docker-compose.yml` — PostgreSQL local.
- `simulador/` — Simulador de dimensionament (web estàtica).
- `docs/` — Documentació del projecte (diagrama entitat-relació, etc.).

## Primers passos

```bash
make setup
cd backend && uv run pre-commit install   # Hook de Git de lint i format (detecta problemes abans de la CI)
```

## Ordres habituals (des de `backend/`)

- Proves: `uv run pytest` (`-v` per veure el nom de cada prova)
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Migracions: consulta `backend/README.md`

## Convencions

- **Claredat del codi**: Escriu sempre codi clar i concís.
- **Abast**: Centra els canvis en la tasca. Evita refactoritzacions que no hi estiguin
  relacionades i abstraccions innecessàries.
- **Documentació**: Per a cada canvi, revisa `README.md` i els fitxers pertinents de `docs/`.
  Actualitza la documentació afectada, mantén els detalls compartits en un sol lloc i
  enllaça'ls en comptes de duplicar el contingut.
- **Commits**: Segueix Conventional Commits, en anglès (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- **Llengua**: Escriu els identificadors en anglès (taules, columnes, funcions, variables i
  noms de proves). Escriu les docstrings i els comentaris dins del codi en català.
- **TDD**: Escriu les proves abans de la implementació sempre que sigui possible. Les proves
  del model s'executen contra una base de dades PostgreSQL real.
- **Comentaris**: Descriu el codi, no la metodologia. No hi afegeixis notes sobre el procés
  ni comparacions d'eines, ni vinculis la documentació a una incidència concreta (ha de
  poder créixer amb el projecte).
- **Entorn**: Es gestiona amb `uv` (no cal activar venv ni pyenv). No incloguis `.env` als commits.
- **Esquema**: Cada canvi a la base de dades ha de passar per una migració d'Alembic. Revisa
  sempre els fitxers generats automàticament i mantén sincronitzat el diagrama de
  `docs/db_schema.md`. Mentre l'esquema no estigui desplegat, regenera la migració inicial
  en comptes d'afegir-ne una segona.
- **Integritat**: Prioritza les garanties de la base de dades (claus foranes, unicitat i CHECK)
  per sobre de la validació a l'aplicació.

## Sol·licituds d'integració (PR)

- Quan se't demani crear una PR, escriu-ne el títol en català.
- A la descripció de la PR, inclou un punt de llista en català per a cada canvi important.
- La descripció ha de contenir només els canvis en punts de llista, sense apartats ni text addicional.
- Si dos canvis són molt similars, agrupa'ls en un únic punt de la descripció de la PR.
