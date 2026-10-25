"""Password hashing (bcrypt) and signed session tokens (JWT)."""
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import bcrypt
import jwt

from app.core.config import get_settings


class TokenError(Exception):
    """The token is missing, malformed, expired or has a bad signature."""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:  # for example a password longer than bcrypt can handle
        return False


@lru_cache
def dummy_hash() -> str:
    """Checked when an email is unknown, so the response time does not reveal which emails exist."""
    return hash_password("not-a-real-password")


def create_access_token(user_id: uuid.UUID, expires_minutes: int | None = None) -> str:
    s = get_settings()
    minutes = s.access_token_expire_minutes if expires_minutes is None else expires_minutes
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError as exc:
        raise TokenError("invalid token") from exc
