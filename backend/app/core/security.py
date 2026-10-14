"""
Password hashing and JWT issuance/verification.

Uses bcrypt via passlib (industry standard, adaptive cost factor) and
PyJWT for JWT signing (replacing python-jose, which is unmaintained and
has known CVEs). Kept isolated from route handlers so the
crypto primitives can be swapped (e.g. to Argon2) without touching
business logic.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT with `sub` claim set to the user id (as string)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Return the subject (user id) encoded in the token, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
