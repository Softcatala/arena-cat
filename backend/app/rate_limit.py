"""Limitador de peticions bàsic en memòria (finestra lliscant).

Protegeix els endpoints sensibles (registre, login, verificació i votació) contra
l'abús limitant el nombre de peticions per clau (IP o usuari) dins d'una finestra.

L'estat es guarda en memòria del procés: és suficient per a un desplegament d'una sola
instància. Per a múltiples instàncies caldria un magatzem compartit (p. ex. Redis).
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from app.config import get_settings
from app.deps import get_current_verified_user
from app.models import User


class RateLimiter:
    """Limita les peticions per clau amb una finestra lliscant en memòria."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Registra una petició per a `key` i llança HTTP 429 si se supera el límit."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                retry_after = int(hits[0] + self.window_seconds - now) + 1
                raise HTTPException(
                    status_code=429,
                    detail="Massa peticions. Torna-ho a provar més tard.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        """Buida l'estat acumulat (útil per als tests)."""
        with self._lock:
            self._hits.clear()


_settings = get_settings()

auth_rate_limiter = RateLimiter(
    _settings.auth_rate_limit_max, _settings.auth_rate_limit_window_seconds
)
vote_rate_limiter = RateLimiter(
    _settings.vote_rate_limit_max, _settings.vote_rate_limit_window_seconds
)


def _client_ip(request: Request) -> str:
    """Retorna l'adreça IP del client, o 'unknown' si no es pot determinar."""
    return request.client.host if request.client else "unknown"


def rate_limit_auth(request: Request) -> None:
    """Limita per IP les peticions d'autenticació (registre, login, verificació)."""
    auth_rate_limiter.check(f"auth:{_client_ip(request)}")


def rate_limit_vote(user: User = Depends(get_current_verified_user)) -> None:
    """Limita la votació per usuari autenticat."""
    vote_rate_limiter.check(f"vote:{user.id}")
