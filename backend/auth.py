"""
Guest sessions: screen-name tokens, no passwords.

How this works:
- A player types a screen name. The backend creates a lightweight player row
  (just an id and the name) and issues a JWT (JSON Web Token) for it.
- A JWT is a signed string that encodes the player's ID and an expiration
  time. The frontend stores it and sends it with every request in the
  Authorization header. The backend can verify the signature without hitting
  the database, and nobody can forge one without JWT_SECRET.
- There is nothing to "log back in" with: lose the token (clear the browser,
  switch devices) and you simply pick a screen name again.
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from .config import settings

# auto_error=False so a missing header gives our 401 below instead of a 403.
bearer_scheme = HTTPBearer(auto_error=False)

SCREEN_NAME_MIN = 2
SCREEN_NAME_MAX = 20


def clean_screen_name(raw: str) -> str:
    """Trim and validate a screen name. Raises 422 with a readable message."""
    name = " ".join(raw.split())  # trim ends and collapse inner whitespace
    if not SCREEN_NAME_MIN <= len(name) <= SCREEN_NAME_MAX:
        raise HTTPException(
            status_code=422,
            detail=f"Screen name must be {SCREEN_NAME_MIN}-{SCREEN_NAME_MAX} characters",
        )
    return name


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired session",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """
    FastAPI dependency that extracts and validates the JWT from the
    Authorization header, returning the player ID encoded inside.
    """
    if creds is None:
        raise _credentials_exception
    try:
        payload = jwt.decode(
            creds.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise _credentials_exception
        return user_id
    except JWTError:
        raise _credentials_exception
