"""Descoberta de revisions de prompts i dels directoris d'inferències associats."""

from pathlib import Path
import re

VERSION_PATTERN = re.compile(r"v([1-9][0-9]{0,30})\Z")


def version_directories(root: Path) -> list[Path]:
    """Retorna els subdirectoris de versió del més nou al més antic."""
    return sorted(
        (
            p
            for p in root.glob("v*")
            if p.is_dir() and VERSION_PATTERN.fullmatch(p.name)
        ),
        key=lambda p: int(p.name[1:]),
        reverse=True,
    )


def latest_prompt_files(root: Path) -> list[Path]:
    """Selecciona l'última revisió de cada prompt o llegeix un directori concret."""
    latest = {}
    for directory in version_directories(root) or [root]:
        for path in directory.glob("*.txt"):
            if path.is_file() and path.stem not in latest:
                latest[path.stem] = path
    return [latest[code] for code in sorted(latest)]


def inference_directory(root: Path, version: str) -> Path:
    """Resol la carpeta d'una revisió sense barrejar directoris de versions diferents."""
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"Versió de prompt no vàlida: {version}")
    if VERSION_PATTERN.fullmatch(root.name):
        if root.name != version:
            raise ValueError(f"El directori {root} no correspon a la versió {version}")
        return root
    return root / version
