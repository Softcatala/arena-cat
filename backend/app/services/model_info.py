from functools import cache
from pathlib import Path

import yaml

INFERENCE_CONFIG = Path(__file__).resolve().parents[3] / "config/inferencia/inferencia_config.yaml"


@cache
def _load_models() -> dict[str, dict]:
    config = yaml.safe_load(INFERENCE_CONFIG.read_text(encoding="utf-8"))
    return {entry["id"]: entry for entry in config["models"]}


def model_presentation(model_id: str) -> dict[str, str | None]:
    """Nom visible, fabricant i enllaç d'un model; sense configuració, usa l'identificador."""
    entry = _load_models().get(model_id)
    if entry is None:
        return {"name": model_id, "maker": None, "url": None}
    return {
        "name": entry.get("display_name", model_id),
        "maker": entry.get("maker"),
        "url": f"https://huggingface.co/{entry['model_name']}",
    }
