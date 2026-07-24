# Comandes de desenvolupament d'Arena Cat. Executa-les des de l'arrel del repositori.

.PHONY: setup db install migrate test dev web http check format inferences load_inferences

setup: db install migrate

db:
	test -f .env || cp .env.example .env
	docker compose up -d --wait

install:
	cd backend && uv sync

migrate:
	cd backend && uv run alembic upgrade head

test:
	cd backend && uv run pytest -v

dev:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

web: dev

http:
	python3 -m http.server 5500 --bind 127.0.0.1 --directory html

check:
	cd backend && uv run ruff check .

format:
	cd backend && uv run ruff format .

inferences:
	uv run python scripts/inferencia.py $(if $(CONFIG),--config $(CONFIG)) $(if $(DEVICE_MAP),--device-map $(DEVICE_MAP))

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
