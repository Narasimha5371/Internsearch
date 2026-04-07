from typing import Any

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from app.core.security import verify_clerk_token


class CurrentUser(BaseModel):
    user_id: str
    email: str | None = None
    raw_claims: dict[str, Any]


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token.")

    token = authorization.split(" ", 1)[1]
    claims = verify_clerk_token(token)
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

    email = claims.get("email") or claims.get("primary_email_address")
    return CurrentUser(user_id=user_id, email=email, raw_claims=claims)
