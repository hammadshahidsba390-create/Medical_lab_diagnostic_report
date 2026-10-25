from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import dummy_hash, hash_password, verify_password
from app.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def register_user(db: Session, email: str, password: str) -> User:
    if get_user_by_email(db, email):
        raise AppError(409, "conflict", "That email is already registered.")
    user = User(email=normalize_email(email), password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two requests with the same email at the same moment
        db.rollback()
        raise AppError(409, "conflict", "That email is already registered.") from None
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    password_ok = verify_password(password, user.password_hash if user else dummy_hash())
    if user is None or not password_ok:
        # One message for both cases, so the response does not reveal which emails exist.
        raise AppError(401, "unauthenticated", "Wrong email or password.")
    return user


def promote_to_admin(db: Session, email: str) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        raise AppError(404, "not_found", "No user with that email.")
    user.role = "admin"
    db.commit()
    return user
