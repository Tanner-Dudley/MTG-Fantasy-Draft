"""
Authentication utilities: password hashing and JWT token management.

How this works:
- When a user registers, we hash their password with BCrypt (a one-way hash).
  We never store the actual password -- only the hash.
- When a user logs in, we hash the password they provide and compare it to the
  stored hash. If they match, we issue a JWT (JSON Web Token).
- A JWT is a signed string that encodes the user's ID and an expiration time.
  The frontend stores it and sends it with every request in the Authorization
  header. The backend can verify the signature without hitting the database.
"""

from datetime import datetime, timedelta, timezone
import re

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def validate_password(password: str) -> str | None:
    """Returns an error message if invalid, or None if OK."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/\\|`~]", password):
        return "Password must contain at least one special character"
    return None


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    FastAPI dependency that extracts and validates the JWT from the
    Authorization header, returning the user ID encoded inside.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise _credentials_exception
        return user_id
    except JWTError:
        raise _credentials_exception
