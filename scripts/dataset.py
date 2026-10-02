"""Consulta les categories, els prompts i les inferències d'una API remota."""

import argparse
from getpass import getpass
import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


def fetch_dataset(api_url: str, token: str) -> dict:
    """Consulta les dades sense reenviar el token en cas de redirecció."""
    request = Request(f"{api_url.rstrip('/')}/dataset")
    if request.type != "https":
        raise ValueError("La URL de l'API ha de fer servir HTTPS")
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "api_url",
        nargs="?",
        default=os.getenv("API_URL"),
        help="URL base de l'API; per defecte, API_URL.",
    )
    parser.add_argument(
        "--show",
        choices=("summary", "all", "categories", "prompts", "inferences"),
        default="summary",
    )
    args = parser.parse_args()
    if not args.api_url:
        parser.error("Indiqueu la URL de l'API o configureu API_URL")
    try:
        token = os.getenv("ADMIN_API_TOKEN") or getpass("ADMIN_API_TOKEN: ")
        data = fetch_dataset(args.api_url, token)
    except (URLError, TimeoutError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    if args.show == "summary":
        fields = {
            "categories": ("id", "code", "name"),
            "prompts": ("id", "code", "version", "category_id"),
            "responses": ("id", "prompt_id", "model", "created_at"),
        }
        for key, columns in fields.items():
            rows = [[str(row[field]) for field in columns] for row in data[key]]
            widths = [max(map(len, values)) for values in zip(columns, *rows)]
            print(f"\n{key} ({len(rows)})")
            for row in [columns, *rows]:
                print(
                    "  ".join(value.ljust(width) for value, width in zip(row, widths))
                )
        return
    if args.show != "all":
        key = "responses" if args.show == "inferences" else args.show
        data = data[key]
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
