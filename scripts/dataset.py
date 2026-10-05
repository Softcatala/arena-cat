"""Consulta les categories, els prompts i les inferències d'una API remota."""

import argparse
from getpass import getpass
import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen


def fetch_dataset(api_url: str, token: str) -> dict:
    """Consulta les dades sense reenviar el token en cas de redirecció."""
    request = Request(f"{api_url.rstrip('/')}/dataset")
    if request.type != "https":
        raise ValueError("La URL de l'API ha de fer servir HTTPS")
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "api_url",
        nargs="?",
        default=os.getenv("API_URL"),
        help="URL base de l'API; per defecte, API_URL.",
    )
    parser.add_argument(
        "--show", choices=("all", "categories", "prompts", "inferences"), default="all"
    )
    args = parser.parse_args()
    if not args.api_url:
        parser.error("Indiqueu la URL de l'API o configureu API_URL")
    try:
        token = os.getenv("ADMIN_API_TOKEN") or getpass("ADMIN_API_TOKEN: ")
        data = fetch_dataset(args.api_url, token)
    except (URLError, TimeoutError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    key = "responses" if args.show == "inferences" else args.show
    print(json.dumps(data if key == "all" else data[key], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
