import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import dummy_hash, hash_password, verify_password
from app.db.session import get_db
from app.main import app
from app.services.auth_service import promote_to_admin


def test_password_hashing():
    h = hash_password("correct horse battery")
    assert h != "correct horse battery" and h.startswith("$2")
    assert verify_password("correct horse battery", h)
    assert not verify_password("wrong", h)
    assert not verify_password("x" * 100, h)  # too long for bcrypt: refused, not an error
    assert hash_password("same") != hash_password("same")  # a new random salt every time
    assert dummy_hash().startswith("$2")


def test_settings_validation():
    with pytest.raises(ValueError):
        Settings(_env_file=None, database_url="sqlite://", jwt_secret="too short")
    s = Settings(_env_file=None, database_url="postgresql://u:p@host:5432/db", jwt_secret="x" * 32)
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"
    s2 = Settings(
        _env_file=None, database_url="postgres://u:p@host/db", jwt_secret="x" * 32,
        allowed_origins="http://a.com, http://b.com",
    )
    assert s2.database_url.startswith("postgresql+psycopg://") and s2.origins == ["http://a.com", "http://b.com"]


def test_error_format_for_unknown_route_and_wrong_method(client):
    r = client.get("/api/v1/nothing")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.get("/api/v1/auth/login")
    assert r.status_code == 405 and r.json()["error"]["code"] == "method_not_allowed"


def test_validation_error_does_not_echo_the_input(client):
    r = client.post("/api/v1/auth/register", json={"email": "bad", "password": "secret-value-123"})
    assert "secret-value-123" not in r.text
    assert r.json()["error"]["details"]


def test_unexpected_errors_are_hidden():
    def boom():
        raise RuntimeError("secret internal detail")

    app.add_api_route("/_boom", boom)
    try:
        r = TestClient(app, raise_server_exceptions=False).get("/_boom")
    finally:
        app.router.routes.pop()
    assert r.status_code == 500
    assert r.json() == {"error": {"code": "internal_error", "message": "Something went wrong. Please try again."}}


def test_health_db_ok(client):
    r = client.get("/health/db")
    assert r.status_code == 200 and r.json()["database"] == "connected"


def test_health_db_reports_unreachable_database():
    class Broken:
        def execute(self, *_):
            raise OperationalError("SELECT 1", {}, Exception("down"))

    def override():
        yield Broken()

    app.dependency_overrides[get_db] = override
    try:
        r = TestClient(app).get("/health/db")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503 and r.json()["error"]["code"] == "database_unavailable"


def test_promote_unknown_user(db_session):
    with pytest.raises(AppError):
        promote_to_admin(db_session, "missing@example.com")


def test_cors_allows_only_the_configured_origin(client):
    def preflight(origin):
        return client.options("/api/v1/me", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})

    ok, other = preflight("http://localhost:3000"), preflight("http://evil.example")
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in other.headers
