# Comandes de desenvolupament d'Arena Cat. Executa-les des de l'arrel del repositori.

.PHONY: setup run test check format inferences load_inferences load_reference_inferences \
	frontend-setup frontend-dev frontend-check

REFERENCE_INFERENCES_WORKTREE ?= ../arena-cat-dades-inferencia
REFERENCE_INFERENCES_BRANCH ?= dades_inferencia
REFERENCE_INFERENCES_DIR ?= $(REFERENCE_INFERENCES_WORKTREE)/data/inferencies/v1

setup:
	test -f .env || cp .env.example .env
	docker compose up -d postgres --wait
	cd backend && uv sync && uv run alembic upgrade head

run:
	test -f .env || cp .env.example .env
	docker compose up --build

test:
	test -f .env || cp .env.example .env
	docker compose up -d postgres --wait
	cd backend && uv run pytest -v

check:
	cd backend && uv run ruff check .

format:
	cd backend && uv run ruff format .

inferences:
	uv run --group inference python scripts/inferencia.py $(if $(CONFIG),--config $(CONFIG)) $(if $(DEVICE_MAP),--device-map $(DEVICE_MAP)) $(if $(FORCE),--force)

# Carrega els prompts i les inferències versionats a la base de dades.
# Per defecte usa data/prompts/v1 i data/inferencies/v1. Es poden sobreescriure
# amb variables d'entorn:
#   make load_inferences
#   PROMPTS_DIR=data/prompts/v2 INFERENCIES_DIR=data/inferencies/v2 make load_inferences
load_inferences:
	uv --project backend run python scripts/carrega_inferencies.py \
		$(if $(PROMPTS_DIR),--prompts-dir $(PROMPTS_DIR)) \
		$(if $(INFERENCIES_DIR),--inferencies-dir $(INFERENCIES_DIR)) \
		$(if $(VERSION),--version $(VERSION))

# Crea, si cal, un worktree amb les inferències de referència i les carrega.
load_reference_inferences:
	@if [ ! -e "$(REFERENCE_INFERENCES_WORKTREE)/.git" ]; then \
		git worktree add "$(REFERENCE_INFERENCES_WORKTREE)" "$(REFERENCE_INFERENCES_BRANCH)"; \
	fi
	$(MAKE) load_inferences INFERENCIES_DIR="$(REFERENCE_INFERENCES_DIR)"

frontend-setup:
	cd frontend && npm ci

frontend-dev:
	cd frontend && npm run dev

frontend-check:
	cd frontend && npm run typecheck && npm run format:check
