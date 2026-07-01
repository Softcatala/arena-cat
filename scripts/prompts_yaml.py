"""Lectura compartida dels fitxers de prompt en YAML.

Tant la canonada d'inferència (``scripts/inferencia.py``) com la càrrega a la
base de dades (``scripts/carrega_inferencies.py``) parteixen dels mateixos
fitxers de prompt. Un fitxer pot ser un escalar de text, un mapa o una llista de
mapes. Centralitzem aquí la normalització perquè les dues vies no divergeixin
(per exemple, que una accepti llistes i l'altra no).
"""

from __future__ import annotations

from typing import Any


def normalize_prompts(data: Any, default_code: str) -> list[dict[str, Any]]:
    """Converteix el contingut d'un fitxer de prompt en una llista d'entrades.

    Accepta els tres formats presents al repositori:

    - un escalar de text: el cos del prompt (el codi és ``default_code``);
    - un mapa amb els camps del prompt (``text`` i, opcionalment, ``code``/``id``);
    - una llista de mapes (diversos prompts en un sol fitxer).

    Args:
        data: Valor ja carregat del YAML.
        default_code: Codi o identificador a assignar quan el prompt no en porta
            (típicament el nom del fitxer sense extensió).

    Returns:
        Llista d'entrades de prompt, cada una un mapa. És buida si ``data`` no és
        cap dels formats reconeguts.
    """
    if isinstance(data, str):
        return [{"id": default_code, "text": data}]
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    return []
