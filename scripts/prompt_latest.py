"""Llista l'última versió disponible de cada prompt."""

from pathlib import Path

from scripts.lib.prompt_versions import latest_prompt_files


def main() -> None:
    prompts = latest_prompt_files(Path("data/prompts"))
    if not prompts:
        print("No s'han trobat prompts a data/prompts")
        return
    print(f"{'prompt':<24} {'versió':<8} camí")
    for path in prompts:
        print(f"{path.stem:<24} {path.parent.name:<8} {path}")


if __name__ == "__main__":
    main()
