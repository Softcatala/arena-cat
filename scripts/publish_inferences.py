"""Copia inferències noves sense modificar les dades publicades."""

import argparse
import shutil
import subprocess
from pathlib import Path


def copy_new_inferences(source: Path, destination: Path, worktree: Path) -> None:
    """Comprova tots els fitxers abans de copiar les inferències noves."""
    source = source.resolve()
    destination = destination.resolve()
    worktree = worktree.resolve()
    if not source.is_dir():
        raise ValueError(f"No existeix el directori d'inferències: {source}")
    if destination != worktree / "data/inferencies":
        raise ValueError("El destí ha de ser data/inferencies dins del worktree.")
    status = subprocess.check_output(
        ["git", "-C", str(worktree), "status", "--porcelain", "--untracked-files=all"],
        text=True,
    )
    if status:
        raise ValueError(
            "El worktree de dades té canvis locals; reviseu-los abans de publicar."
        )

    new_files = []
    conflicts = []
    for file in sorted(source.rglob("*")):
        if not file.is_file():
            continue
        target = destination / file.relative_to(source)
        if target.exists():
            if not target.is_file() or file.read_bytes() != target.read_bytes():
                conflicts.append(str(file.relative_to(source)))
        else:
            new_files.append((file, target))
    if conflicts:
        raise ValueError(
            "Les inferències publicades no es poden modificar; publiqueu una versió nova:\n"
            + "\n".join(conflicts)
        )
    for file, target in new_files:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)


def main() -> None:
    """Valida els arguments i prepara les inferències per publicar."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    args = parser.parse_args()
    try:
        copy_new_inferences(args.source, args.destination, args.worktree)
    except ValueError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
