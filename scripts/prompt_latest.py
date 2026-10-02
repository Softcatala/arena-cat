"""Llista l'última versió disponible de cada prompt."""

import argparse
from pathlib import Path

from scripts.lib.prompt_versions import latest_prompt_files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts-dir", type=Path, default=Path("data/prompts"))
    args = parser.parse_args()
    prompts = latest_prompt_files(args.prompts_dir)
    if not prompts:
        print(f"No s'han trobat prompts a {args.prompts_dir}")
        return
    print(f"{'prompt':<24} {'versió':<8} camí")
    for path in prompts:
        print(f"{path.stem:<24} {path.parent.name:<8} {path}")


if __name__ == "__main__":
    main()
