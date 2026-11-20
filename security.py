import os
import re
import secrets
from typing import Annotated

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",
    description="Clé configurée dans la variable d'environnement API_KEY du serveur.",
    auto_error=False,
)


def load_api_key() -> bytes:
    key = os.environ.get("API_KEY", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", key):
        raise RuntimeError(
            "Configurez API_KEY avec une clé aléatoire de 32 à 128 caractères "
            "(lettres ASCII, chiffres, tirets ou underscores)."
        )
    return key.encode("ascii")


def require_api_key(
    request: Request,
    api_key: Annotated[str | None, Security(api_key_header)],
) -> None:
    # Comparer des octets évite une erreur sur un en-tête non ASCII.
    if (
        len(request.headers.getlist("x-api-key")) != 1
        or not api_key
        or not secrets.compare_digest(api_key.encode("utf-8"), request.app.state.api_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API absente ou invalide.",
            headers={"WWW-Authenticate": "APIKey"},
        )
