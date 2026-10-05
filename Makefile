# Comandes de desenvolupament d'Arena Cat. Executa-les des de l'arrel del repositori.

.PHONY: setup run test check format inferences analyze_inferences publish_inferences load_inferences load_reference_inferences \
	copy_reference_inferences prompt_latest dataset frontend-setup frontend-dev frontend-check

REFERENCE_INFERENCES_WORKTREE ?= ../arena-cat-dades-inferencia
REFERENCE_INFERENCES_BRANCH ?= dades_inferencia
REFERENCE_INFERENCES_DIR ?= $(REFERENCE_INFERENCES_WORKTREE)/data/inferencies
LOCAL_INFERENCES_DIR ?= data/inferencies
PUBLISH_INFERENCES_DIR ?= data/inferencies
PUBLISH_INFERENCES_COMMIT_MESSAGE ?= data: publish new inferences

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

# Paràmetres opcionals: CONFIG, DEVICE_MAP, CATEGORY i FORCE.
# Exemple: make inferences CATEGORY=traduccio
inferences:
	uv run --group inference python scripts/inferencia.py $(if $(CONFIG),--config $(CONFIG)) $(if $(DEVICE_MAP),--device-map $(DEVICE_MAP)) $(if $(CATEGORY),--prompt-prefix $(CATEGORY)_) $(if $(FORCE),--force)

# Llista l'última versió de cada prompt de data/prompts.
prompt_latest:
	uv run python -m scripts.prompt_latest

# Consulta l'API remota amb la configuració de .env; API_URL i SHOW permeten sobreescriure-la.
dataset:
	@uv run $(if $(wildcard .env),--env-file .env) python -m scripts.dataset $(if $(API_URL),"$(API_URL)") $(if $(SHOW),--show "$(SHOW)")

# Genera results.txt; INFERENCIES_DIR permet seleccionar un altre directori.
analyze_inferences:
	uv run --group scripts python scripts/analitza_inferencies.py $(if $(INFERENCIES_DIR),--inferencies "$(INFERENCIES_DIR)") $(if $(PROMPTS_DIR),--prompts-dir "$(PROMPTS_DIR)")

# Copia les inferències de referència al directori local, sobreescrivint coincidències.
copy_reference_inferences:
	@if [ ! -e "$(REFERENCE_INFERENCES_WORKTREE)/.git" ]; then \
		git worktree add "$(REFERENCE_INFERENCES_WORKTREE)" "$(REFERENCE_INFERENCES_BRANCH)"; \
	fi
	test -d "$(REFERENCE_INFERENCES_DIR)"
	mkdir -p "$(LOCAL_INFERENCES_DIR)"
	cp -R "$(REFERENCE_INFERENCES_DIR)/." "$(LOCAL_INFERENCES_DIR)/"

# Publica només inferències noves; les revisions requereixen una versió nova.
publish_inferences:
	test -d "$(PUBLISH_INFERENCES_DIR)"
	@if [ ! -e "$(REFERENCE_INFERENCES_WORKTREE)/.git" ]; then \
		git worktree add "$(REFERENCE_INFERENCES_WORKTREE)" "$(REFERENCE_INFERENCES_BRANCH)"; \
	fi
	@status=$$(git -C "$(REFERENCE_INFERENCES_WORKTREE)" status --porcelain --untracked-files=all) || exit 1; \
	if [ -n "$$status" ]; then \
		echo "El worktree de dades té canvis locals; reviseu-los abans de publicar." >&2; \
		exit 1; \
	fi
	git -C "$(REFERENCE_INFERENCES_WORKTREE)" pull --ff-only
	python3 scripts/publish_inferences.py --source "$(PUBLISH_INFERENCES_DIR)" \
		--destination "$(REFERENCE_INFERENCES_DIR)" --worktree "$(REFERENCE_INFERENCES_WORKTREE)"
	git -C "$(REFERENCE_INFERENCES_WORKTREE)" add data/inferencies
	@if git -C "$(REFERENCE_INFERENCES_WORKTREE)" diff --cached --quiet; then \
		echo "No hi ha inferències noves per publicar."; \
	else \
		git -C "$(REFERENCE_INFERENCES_WORKTREE)" commit -m "$(PUBLISH_INFERENCES_COMMIT_MESSAGE)"; \
		git -C "$(REFERENCE_INFERENCES_WORKTREE)" push; \
	fi

# Carrega els prompts i les inferències versionats a la base de dades.
# Per defecte carrega totes les versions de data/prompts i data/inferencies.
# Es poden sobreescriure els directoris
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
