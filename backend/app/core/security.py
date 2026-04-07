import time
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import jwt

from app.core.config import settings

_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


def _get_jwks() -> dict[str, Any]:
    if not settings.clerk_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_JWKS_URL is not configured.",
        )

    now = time.time()
    if _JWKS_CACHE["keys"] and now - _JWKS_CACHE["fetched_at"] < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]

    with httpx.Client(timeout=10) as client:
        response = client.get(settings.clerk_jwks_url)

    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Unable to fetch Clerk JWKS.")

    jwks = response.json()
    _JWKS_CACHE["keys"] = jwks
    _JWKS_CACHE["fetched_at"] = now
    return jwks


def verify_clerk_token(token: str) -> dict[str, Any]:
    if not settings.clerk_issuer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_ISSUER is not configured.",
        )

    try:
        headers = jwt.get_unverified_header(token)
    except jwt.JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token header.") from exc

    kid = headers.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Missing token key id.")

    alg = headers.get("alg")
    if alg != "RS256":
        raise HTTPException(status_code=401, detail="Unsupported token signing algorithm.")

    jwks = _get_jwks()
    keys = jwks.get("keys", [])
    key = next((item for item in keys if item.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=401, detail="Signing key not found.")

    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},
        )
    except jwt.JWTError as exc:
        raise HTTPException(status_code=401, detail="Token verification failed.") from exc
