import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import promote_to_admin


def test_register_creates_user_without_exposing_password(client, register, db_session):
    r = register("Hammad@Example.com", "correct horse battery")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "hammad@example.com"  # stored in lower case
    assert body["role"] == "user"
    assert "password" not in body and "password_hash" not in body
    stored = db_session.scalar(select(User))
    assert stored.password_hash.startswith("$2")  # a bcrypt hash
    assert "correct horse battery" not in stored.password_hash


def test_duplicate_email_is_rejected_ignoring_case(register):
    assert register("a@example.com").status_code == 201
    r = register("A@EXAMPLE.com")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_register_validation(client):
    bad_email = client.post("/api/v1/auth/register", json={"email": "nope", "password": "correct horse battery"})
    short = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "short"})
    long = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "x" * 80})
    multibyte = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "é" * 40})
    for r in (bad_email, short, long, multibyte):
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"


def test_login_returns_token_that_works(client, auth_header):
    headers = auth_header()
    r = client.get("/api/v1/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"


def test_login_token_response_shape(client, register):
    register()
    r = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "correct horse battery"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 3600 and body["access_token"]


def test_wrong_password_and_unknown_email_give_the_same_answer(client, register):
    register()
    wrong = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "wrong password"})
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong password"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_me_requires_a_valid_token(client, db_session):
    assert client.get("/api/v1/me").status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": "Basic abc"}).status_code == 401


def test_expired_token_is_rejected(client, register, db_session):
    register()
    user = db_session.scalar(select(User))
    expired = create_access_token(user.id, expires_minutes=-1)
    r = client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_tampered_or_foreign_tokens_are_rejected(client, register, db_session):
    register()
    user = db_session.scalar(select(User))
    claims = {"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    wrong_key = jwt.encode(claims, "another-secret-another-secret-123456", "HS256")
    no_signature = jwt.encode(claims, None, "none")
    unknown_user = create_access_token(uuid.uuid4())
    bad_subject = jwt.encode(
        {"sub": "not-a-uuid", "exp": datetime.now(UTC) + timedelta(minutes=5)}, get_settings().jwt_secret, "HS256"
    )
    for token in (wrong_key, no_signature, unknown_user, bad_subject):
        assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_logout_requires_login_and_returns_204(client, auth_header):
    assert client.post("/api/v1/auth/logout").status_code == 401
    assert client.post("/api/v1/auth/logout", headers=auth_header()).status_code == 204


def test_users_are_separate(client, auth_header):
    a = client.get("/api/v1/me", headers=auth_header("a@example.com")).json()
    b = client.get("/api/v1/me", headers=auth_header("b@example.com")).json()
    assert a["id"] != b["id"] and a["email"] != b["email"]


def test_admin_guard_and_promotion(db_session):
    mini = FastAPI()
    register_error_handlers(mini)

    @mini.get("/admin-only")
    def admin_only(user: User = Depends(require_admin)):
        return {"ok": True}

    def override():
        yield db_session

    mini.dependency_overrides[get_db] = override
    api = TestClient(mini)
    user = User(email="boss@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
    assert api.get("/admin-only", headers=headers).status_code == 403
    promote_to_admin(db_session, "boss@example.com")
    assert api.get("/admin-only", headers=headers).status_code == 200  # role is read from the database
    assert api.get("/admin-only").status_code == 401
