# Script idempotent d'upsert a la base de dades
from pathlib import Path

import yaml

# Dins de scripts/carrega_inferencies.py, canviar la secció de lectura a:
inferencies_files = Path("data/inferencies/v1").rglob("*.yaml")
for file_path in inferencies_files:
    with file_path.open("r", encoding="utf-8") as f:
        inf = yaml.safe_load(f)

    prompt_id = inf["prompt"]["id"]
    model_id = inf["model"]["id"]

    # El text final separat va a la base de dades
    text_resposta = inf["output"]["answer"]
    # El contingut del raonament s'emmagatzema o es deixa en blanc per a l'avaluació cega
    # ... executa l'upsert tal com s'havia dissenyat a la taula `respostes` ...
