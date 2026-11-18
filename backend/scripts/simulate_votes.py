"""Simula usuaris que voten a través de l'API.

Crea els usuaris (o reutilitza els existents amb el mateix prefix), supera la
prova d'acreditació amb `?debug` i emet vots aleatoris. Cal el servidor en marxa.

Ús: uv run python scripts/simulate_votes.py [--users 20] [--votes 20] [--prefix sim]
"""

import argparse
import json
import random
import threading
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

PASSWORD = "Simulat1234"
VOTE_DELAY_SECONDS = 10.5  # L'API exigeix 10 s entre rebre la tasca i votar.


def make_client(base_url: str):
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
        request = urllib.request.Request(
            base_url + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
        )
        try:
            with opener.open(request) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode()

    return call


def simulate_user(base_url: str, email: str, votes: int) -> int:
    """Registra l'usuari, l'acredita i hi emet els vots. Retorna els vots emesos."""
    call = make_client(base_url)
    call("POST", "/auth/register", {"email": email, "password": PASSWORD, "consent": True})
    status, body = call("POST", "/auth/login", {"email": email, "password": PASSWORD})
    assert status == 200, (status, body)
    _, questionnaire = call("GET", "/qualification")
    call(
        "POST",
        "/qualification?debug",
        {"answers": {q["id"]: "A" for q in questionnaire["questions"]}},
    )
    cast = 0
    while cast < votes:
        status, task = call("GET", "/task")
        if status != 200:
            print(f"{email}: /task -> {status} {task}")
            break
        time.sleep(VOTE_DELAY_SECONDS)
        winner = random.choice(["a", "b", "tie", "neither"])
        status, body = call("POST", "/vote", {"winner": winner, "token": task["token"]})
        if status != 200:
            print(f"{email}: /vote -> {status} {body}")
            break
        cast += 1
    print(f"{email}: {cast} vots")
    return cast


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://localhost:8000/api")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--votes", type=int, default=20)
    parser.add_argument("--prefix", default="sim", help="Prefix dels correus (@example.com)")
    args = parser.parse_args()

    results = [0] * args.users

    def worker(index: int) -> None:
        email = f"{args.prefix}-{index}@example.com"
        results[index] = simulate_user(args.base_url, email, args.votes)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(args.users)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print("total vots:", sum(results))


if __name__ == "__main__":
    main()
