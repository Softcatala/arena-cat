"""Importació d'inferències des dels fitxers YAML de la canonada d'inferència.

Aplica les mateixes regles que `scripts/carrega_inferencies.py` (clau `(prompt_id, model)`,
cap mutació d'una resposta existent) perquè carregar un fitxer des d'aquí o des de la línia
d'ordres doni el mateix resultat.
"""

import hashlib
from dataclasses import dataclass
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from app.models import Prompt, Response
from app.schemas import ImportFileResult, ImportResponsesRequest, ImportResponsesResponse


class ImportFileError(Exception):
    """Un fitxer no es pot importar; el missatge s'ensenya a l'administrador."""


@dataclass(slots=True)
class ParsedInference:
    prompt_code: str
    model: str
    text: str
    metadata: dict[str, Any]
    prompt_sha256: str | None


def _nested(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _require(value: Any, message: str) -> Any:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ImportFileError(message)
    return value


def parse_inference(content: str) -> ParsedInference:
    """Llegeix el contingut d'un fitxer d'inferència i el normalitza."""
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        raise ImportFileError("El fitxer no és un YAML vàlid") from None
    if not isinstance(data, dict):
        raise ImportFileError("La inferència ha de ser un mapa")

    prompt_code = _require(_nested(data, "prompt", "id"), "Falta prompt.id")
    model = _require(_nested(data, "model", "id"), "Falta model.id")
    answer = _require(_nested(data, "output", "answer"), "Falta output.answer")

    metadata = {
        "model_name": _nested(data, "model", "model_name"),
        "revision": _nested(data, "model", "revision"),
        "generation": data.get("generation"),
        "run": data.get("run"),
        "backend": data.get("backend"),
        "prompt_sha256": _nested(data, "prompt", "sha256"),
        "reasoning": _nested(data, "reasoning", "content"),
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}
    prompt_sha256 = _nested(data, "prompt", "sha256")

    return ParsedInference(
        prompt_code=str(prompt_code),
        model=str(model),
        text=str(answer).strip(),
        metadata=metadata,
        prompt_sha256=str(prompt_sha256) if prompt_sha256 is not None else None,
    )


def _prompt_hash_matches(prompt: Prompt, expected: str) -> bool:
    """Compara amb el hash del text del prompt, tal com el calcula la canonada.

    La canonada el calcula sobre el contingut del fitxer `.txt` llegit en mode text, que
    converteix `\r\n` en `\n` i conserva les línies en blanc finals. La base de dades en desa
    el text sense espais als extrems, així que s'accepten fins a tres salts de línia finals.
    """
    return any(
        hashlib.sha256((prompt.text + ending).encode("utf-8")).hexdigest() == expected.lower()
        for ending in ("", "\n", "\n\n", "\n\n\n")
    )


def _import_one(db: OrmSession, version: str, content: str) -> str:
    """Importa un fitxer i retorna `inserted` o `skipped`; falla amb `ImportFileError`."""
    record = parse_inference(content)

    prompt = db.scalar(
        select(Prompt).where(Prompt.version == version, Prompt.code == record.prompt_code)
    )
    if prompt is None:
        raise ImportFileError(f"Prompt desconegut ({version}/{record.prompt_code})")
    if record.prompt_sha256 is not None and not _prompt_hash_matches(prompt, record.prompt_sha256):
        raise ImportFileError(
            f"El hash del prompt no coincideix amb el text actual de {version}/{record.prompt_code}"
        )

    existing = db.scalar(
        select(Response).where(Response.prompt_id == prompt.id, Response.model == record.model)
    )
    if existing is not None:
        if existing.text == record.text and existing.inference_metadata == record.metadata:
            return "skipped"
        raise ImportFileError(
            f"La resposta de {record.model} a {record.prompt_code} ja existeix amb un contingut "
            "diferent; publiqueu-la amb una versió nova"
        )

    db.add(
        Response(
            prompt_id=prompt.id,
            model=record.model,
            text=record.text,
            inference_metadata=record.metadata,
        )
    )
    db.flush()
    return "inserted"


def import_responses(db: OrmSession, payload: ImportResponsesRequest) -> ImportResponsesResponse:
    """Importa cada fitxer de manera independent: els errors d'un no aturen els altres."""
    results: list[ImportFileResult] = []
    for item in payload.files:
        try:
            with db.begin_nested():
                status = _import_one(db, payload.version, item.content)
            results.append(ImportFileResult(name=item.name, status=status))
        except ImportFileError as error:
            results.append(ImportFileResult(name=item.name, status="error", detail=str(error)))
        except IntegrityError:
            results.append(
                ImportFileResult(
                    name=item.name, status="error", detail="No s'ha pogut desar la inferència"
                )
            )
    db.commit()

    return ImportResponsesResponse(
        inserted=sum(item.status == "inserted" for item in results),
        skipped=sum(item.status == "skipped" for item in results),
        errors=sum(item.status == "error" for item in results),
        files=results,
    )
