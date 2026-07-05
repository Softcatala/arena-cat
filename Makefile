# Comandes de desenvolupament d'Arena Cat. Executa-les des de l'arrel del repositori.

.PHONY: load_inferences run_inferences metrics

run_inferences:
	uv run python scripts/inferencia.py \
		$(if $(CONFIG),--config $(CONFIG)) \
		$(if $(DEVICE_MAP),--device-map $(DEVICE_MAP)) \
		$(if $(LOG_LEVEL),--log-level $(LOG_LEVEL))

metrics:
	uv run python scripts/analitza_inferencies.py \
		$(if $(INFERENCIES_DIR),--inferencies $(INFERENCIES_DIR))

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
