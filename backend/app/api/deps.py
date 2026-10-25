import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


def _unauthenticated() -> AppError:
    return AppError(401, "unauthenticated", "Please log in again.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthenticated()
    try:
        user_id = uuid.UUID(decode_access_token(credentials.credentials)["sub"])
    except (TokenError, ValueError):
        raise _unauthenticated() from None
    user = db.get(User, user_id)
    if user is None:
        raise _unauthenticated()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    # The role is read from the database on every request, not from the token.
    if user.role != "admin":
        raise AppError(403, "forbidden", "You do not have access to this page.")
    return user
