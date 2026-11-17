"""Concedeix o revoca el rol d'administrador d'un compte.

El rol no es pot canviar des de cap endpoint: aquesta ordre és la manera d'assignar-lo,
sobretot per al primer administrador d'un entorn. Cal que el compte existeixi, tingui el
correu verificat i no estigui bloquejat ni donat de baixa. Es pot executar més d'una
vegada: si el compte ja té l'estat demanat, no canvia res.

La connexió i la clau amb què es calcula el hash del correu (``EMAIL_HASH_PEPPER``) es
resolen amb la mateixa configuració que el servei (``app.config``), de manera que també
funciona dins del contenidor de l'API.

Ús, des de ``backend/``::

    uv run python -m app.cli.admin correu@exemple.cat
    uv run python -m app.cli.admin correu@exemple.cat --revoca
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_sessionmaker
from app.models import User
from app.security import compute_email_hash

GRANTED = "granted"
REVOKED = "revoked"
UNCHANGED = "unchanged"

MESSAGES = {
    GRANTED: "El compte ara és administrador.",
    REVOKED: "El compte ja no és administrador.",
    UNCHANGED: "No cal cap canvi: el compte ja tenia aquest estat.",
}


class AdministratorError(Exception):
    """El compte no es pot canviar; el missatge s'ensenya a qui executa l'ordre."""


def set_administrator(session: Session, email: str, revoke: bool = False) -> str:
    """Concedeix (o revoca, amb ``revoke``) el rol d'administrador al compte del correu.

    Retorna ``GRANTED``, ``REVOKED`` o ``UNCHANGED``. Fa ``flush`` però no ``commit``.
    """
    user = session.scalar(select(User).where(User.email_hash == compute_email_hash(email)))
    if user is None:
        raise AdministratorError("No existeix cap compte amb aquest correu.")

    if revoke:
        if not user.is_admin:
            return UNCHANGED
        user.is_admin = False
        session.flush()
        return REVOKED

    if user.deleted_at is not None:
        raise AdministratorError("El compte s'ha donat de baixa.")
    if user.email_verified_at is None:
        raise AdministratorError("El correu del compte no està verificat.")
    if user.blocked_at is not None:
        raise AdministratorError("El compte està bloquejat.")
    if user.is_admin:
        return UNCHANGED
    user.is_admin = True
    session.flush()
    return GRANTED


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Concedeix o revoca el rol d'administrador d'un compte."
    )
    parser.add_argument("email", help="Correu del compte.")
    parser.add_argument(
        "--revoca",
        action="store_true",
        help="Treu el rol d'administrador en lloc de concedir-lo.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Punt d'entrada CLI; retorna ``0`` si ha anat bé i ``1`` si no s'ha pogut canviar."""
    args = parse_args(argv)
    with get_sessionmaker()() as session:
        try:
            result = set_administrator(session, args.email, args.revoca)
        except AdministratorError as error:
            print(error, file=sys.stderr)
            return 1
        session.commit()
    print(MESSAGES[result])
    return 0


if __name__ == "__main__":
    sys.exit(main())
