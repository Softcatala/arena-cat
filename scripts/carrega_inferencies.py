"""Càrrega idempotent de prompts i inferències a la base de dades.

Llegeix els prompts versionats a ``data/prompts/<version>/*.yaml`` i les
inferències a ``data/inferencies/<version>/<model_id>/*.yaml``, i en fa *upsert*
a les taules ``prompts`` i ``responses``. La clau natural d'un prompt és
``(version, code)`` i la d'una resposta ``(prompt_id, model)``, de manera que
tornar a executar l'script no duplica files ni en trenca les restriccions.

La connexió es resol amb la mateixa configuració que el servei (``app.config``),
és a dir el rol d'aplicació amb permisos limitats.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
# El model de dades i la configuració viuen al paquet backend/app.
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import get_sessionmaker  # noqa: E402
from app.models import Category, Prompt, Response  # noqa: E402

LOGGER = logging.getLogger("carrega_inferencies")

DEFAULT_VERSION = "v1"
DEFAULT_PROMPTS_DIR = REPO_ROOT / "data" / "prompts" / DEFAULT_VERSION
DEFAULT_INFERENCIES_DIR = REPO_ROOT / "data" / "inferencies" / DEFAULT_VERSION

# El codi d'un prompt acaba amb un sufix numèric (p. ex. ``traduccio_10``); la
# resta identifica la categoria (``traduccio``).
_CODE_SUFFIX = re.compile(r"_\d+$")


class SchemaError(Exception):
    """Un fitxer YAML no compleix l'esquema esperat.

    Es fa servir per a camps obligatoris absents, tipus inesperats o referències
    a entitats desconegudes (categoria o prompt).
    """


@dataclass
class PromptRecord:
    """Prompt normalitzat, a punt per fer *upsert* a la taula ``prompts``."""

    version: str
    code: str
    category_code: str
    text: str
    source: Path


@dataclass
class ResponseRecord:
    """Resposta d'un model normalitzada, per fer *upsert* a ``responses``."""

    version: str
    prompt_code: str
    model: str
    text: str
    metadata: dict[str, Any]
    source: Path


@dataclass
class Stats:
    """Recompte d'un tipus d'entitat carregada."""

    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


@dataclass
class Summary:
    """Resum global de la càrrega."""

    prompts: Stats
    responses: Stats

    @property
    def total_errors(self) -> int:
        return self.prompts.errors + self.responses.errors


def _require(value: Any, message: str, source: Path) -> Any:
    """Comprova que un camp obligatori hi és i no és buit.

    Args:
        value: Valor llegit del YAML.
        message: Descripció de l'incompliment per al missatge d'error.
        source: Fitxer d'origen, per situar l'error.

    Returns:
        El valor original si és vàlid.

    Raises:
        SchemaError: Si el valor és ``None`` o una cadena buida.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise SchemaError(f"{source}: {message}")
    return value


def _nested(data: Any, *keys: str) -> Any:
    """Accedeix a una clau imbricada sense petar si falta un nivell.

    Args:
        data: Estructura carregada del YAML.
        *keys: Seqüència de claus a recórrer.

    Returns:
        El valor trobat, o ``None`` si qualsevol nivell no és un mapa o no hi és.
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def category_code_for(code: str) -> str:
    """Deriva el codi de categoria a partir del codi de prompt.

    Args:
        code: Codi del prompt (p. ex. ``traduccio_10``).

    Returns:
        Codi de categoria (p. ex. ``traduccio``).
    """
    return _CODE_SUFFIX.sub("", code)


def parse_prompt_file(path: Path, version: str) -> PromptRecord:
    """Llegeix un fitxer de prompt i el normalitza.

    Accepta tant un escalar de text (el cos del prompt) com un mapa amb els camps
    ``code``/``id``, ``text`` i, opcionalment, ``category``.

    Args:
        path: Fitxer YAML del prompt.
        version: Versió del conjunt de dades.

    Returns:
        Prompt normalitzat.

    Raises:
        SchemaError: Si el contingut no és text ni mapa, o no té text.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if isinstance(data, str):
        code = path.stem
        text = data
        category_code = category_code_for(code)
    elif isinstance(data, dict):
        code = str(data.get("code") or data.get("id") or path.stem)
        text = data.get("text")
        category_code = str(data.get("category") or category_code_for(code))
    else:
        raise SchemaError(f"{path}: el prompt ha de ser un text o un mapa")

    text = _require(text, "el prompt no té text", path)
    return PromptRecord(
        version=version,
        code=code,
        category_code=category_code,
        text=text.strip(),
        source=path,
    )


def parse_inference_file(path: Path, version: str) -> ResponseRecord:
    """Llegeix un fitxer d'inferència i el normalitza.

    Args:
        path: Fitxer YAML d'inferència (sortida de la canonada).
        version: Versió del conjunt de dades.

    Returns:
        Resposta normalitzada. El raonament intern es desa a les metadades, no al
        text visible, perquè l'avaluació és a cegues.

    Raises:
        SchemaError: Si no és un mapa o falta ``prompt.id``, ``model.id`` o
            ``output.answer``.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaError(f"{path}: la inferència ha de ser un mapa")

    prompt_code = _require(_nested(data, "prompt", "id"), "falta prompt.id", path)
    model = _require(_nested(data, "model", "id"), "falta model.id", path)
    answer = _require(_nested(data, "output", "answer"), "falta output.answer", path)

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

    return ResponseRecord(
        version=version,
        prompt_code=str(prompt_code),
        model=str(model),
        text=str(answer).strip(),
        metadata=metadata,
        source=path,
    )


def upsert_prompt(
    session: Session,
    record: PromptRecord,
    category_ids: dict[str, int],
    stats: Stats,
) -> None:
    """Fa *upsert* d'un prompt per la clau ``(version, code)``.

    Args:
        session: Sessió de base de dades activa.
        record: Prompt normalitzat.
        category_ids: Mapa de codi de categoria a identificador.
        stats: Recompte que s'actualitza segons el resultat.
    """
    category_id = category_ids.get(record.category_code)
    if category_id is None:
        LOGGER.error("%s: categoria desconeguda '%s'", record.source, record.category_code)
        stats.errors += 1
        return

    existing = session.scalar(
        select(Prompt).where(Prompt.version == record.version, Prompt.code == record.code)
    )
    if existing is None:
        session.add(
            Prompt(
                version=record.version,
                code=record.code,
                category_id=category_id,
                text=record.text,
            )
        )
        session.flush()
        stats.inserted += 1
    elif existing.text != record.text or existing.category_id != category_id:
        existing.text = record.text
        existing.category_id = category_id
        session.flush()
        stats.updated += 1
    else:
        stats.skipped += 1


def upsert_response(session: Session, record: ResponseRecord, stats: Stats) -> None:
    """Fa *upsert* d'una resposta per la clau ``(prompt_id, model)``.

    Args:
        session: Sessió de base de dades activa.
        record: Resposta normalitzada.
        stats: Recompte que s'actualitza segons el resultat.
    """
    prompt = session.scalar(
        select(Prompt).where(Prompt.version == record.version, Prompt.code == record.prompt_code)
    )
    if prompt is None:
        LOGGER.error(
            "%s: prompt desconegut (%s/%s)", record.source, record.version, record.prompt_code
        )
        stats.errors += 1
        return

    existing = session.scalar(
        select(Response).where(Response.prompt_id == prompt.id, Response.model == record.model)
    )
    if existing is None:
        session.add(
            Response(
                prompt_id=prompt.id,
                model=record.model,
                text=record.text,
                inference_metadata=record.metadata,
            )
        )
        session.flush()
        stats.inserted += 1
    elif existing.text != record.text or existing.inference_metadata != record.metadata:
        existing.text = record.text
        existing.inference_metadata = record.metadata
        session.flush()
        stats.updated += 1
    else:
        stats.skipped += 1


def load_prompts(
    session: Session,
    prompts_dir: Path,
    version: str,
    category_ids: dict[str, int],
    stats: Stats,
) -> None:
    """Carrega tots els prompts d'un directori.

    Args:
        session: Sessió de base de dades activa.
        prompts_dir: Directori amb els fitxers de prompt.
        version: Versió del conjunt de dades.
        category_ids: Mapa de codi de categoria a identificador.
        stats: Recompte que s'actualitza.
    """
    for path in sorted(prompts_dir.glob("*.yaml")):
        try:
            record = parse_prompt_file(path, version)
        except (SchemaError, yaml.YAMLError) as error:
            LOGGER.error("prompt no vàlid: %s", error)
            stats.errors += 1
            continue
        upsert_prompt(session, record, category_ids, stats)


def load_responses(session: Session, inferencies_dir: Path, version: str, stats: Stats) -> None:
    """Carrega totes les inferències d'un directori (recursivament).

    Args:
        session: Sessió de base de dades activa.
        inferencies_dir: Directori arrel de les inferències.
        version: Versió del conjunt de dades.
        stats: Recompte que s'actualitza.
    """
    for path in sorted(inferencies_dir.rglob("*.yaml")):
        try:
            record = parse_inference_file(path, version)
        except (SchemaError, yaml.YAMLError) as error:
            LOGGER.error("inferència no vàlida: %s", error)
            stats.errors += 1
            continue
        upsert_response(session, record, stats)


def run_load(
    session: Session,
    prompts_dir: Path | str,
    inferencies_dir: Path | str,
    version: str | None = None,
) -> Summary:
    """Carrega prompts i inferències dins de la sessió donada.

    No fa ``commit``: és responsabilitat de qui crida la funció (la CLI confirma
    la transacció; els tests la desfan).

    Args:
        session: Sessió de base de dades activa.
        prompts_dir: Directori dels prompts.
        inferencies_dir: Directori arrel de les inferències.
        version: Versió del conjunt de dades. Si és ``None``, es dedueix del nom
            del directori de prompts (p. ex. ``data/prompts/v1`` -> ``v1``).

    Returns:
        Resum amb els recomptes de prompts i respostes.
    """
    prompts_dir = Path(prompts_dir)
    inferencies_dir = Path(inferencies_dir)
    version = version or prompts_dir.name

    category_ids = {category.code: category.id for category in session.scalars(select(Category))}

    summary = Summary(prompts=Stats(), responses=Stats())
    load_prompts(session, prompts_dir, version, category_ids, summary.prompts)
    load_responses(session, inferencies_dir, version, summary.responses)
    return summary


def _format_stats(stats: Stats) -> str:
    return (
        f"inserits={stats.inserted} actualitzats={stats.updated} "
        f"omesos={stats.skipped} errors={stats.errors}"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Llegeix els paràmetres CLI.

    Args:
        argv: Arguments alternatius (per a tests); ``None`` usa ``sys.argv``.

    Returns:
        Namespace amb els paràmetres.
    """
    parser = argparse.ArgumentParser(
        description="Càrrega idempotent de prompts i inferències a la base de dades.",
    )
    parser.add_argument(
        "--prompts-dir",
        type=Path,
        default=DEFAULT_PROMPTS_DIR,
        help="Directori amb els fitxers YAML de prompts.",
    )
    parser.add_argument(
        "--inferencies-dir",
        type=Path,
        default=DEFAULT_INFERENCIES_DIR,
        help="Directori arrel amb les inferències (un subdirectori per model).",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Versió del conjunt de dades. Per defecte, el nom del directori de prompts.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Nivell mínim dels missatges de logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Punt d'entrada CLI.

    Args:
        argv: Arguments alternatius (per a tests); ``None`` usa ``sys.argv``.

    Returns:
        ``0`` si tot ha anat bé, ``1`` si algun fitxer no complia l'esquema.
    """
    args = parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s:%(name)s:%(message)s")

    with get_sessionmaker()() as session:
        summary = run_load(session, args.prompts_dir, args.inferencies_dir, args.version)
        session.commit()

    print(f"Prompts:   {_format_stats(summary.prompts)}")
    print(f"Respostes: {_format_stats(summary.responses)}")

    if summary.total_errors:
        LOGGER.error("S'han trobat %s fitxers no vàlids.", summary.total_errors)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
