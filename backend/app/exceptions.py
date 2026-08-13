from fastapi import HTTPException

# Codi que el frontend fa servir per distingir aquest cas d'una sessió caducada:
# el 401 és del token de tasca (curt i d'un sol ús), no de la cookie de sessió,
# així que no ha de forçar cap desconnexió.
TASK_TOKEN_INVALID = "task_token_invalid"


class TaskTokenError(HTTPException):
    """401 pel token de tasca (`/vote`, `/task/skip`), no per la sessió.

    Es distingeix dels 401 de sessió invàlida amb el camp `error_code` de la
    resposta (vegeu el gestor a `main.py`), perquè el frontend no confongui un
    token de tasca caducat amb una sessió tancada.
    """

    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)
