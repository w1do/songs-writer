import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import auth
from app.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "admin_password", "correct-password")
    monkeypatch.setattr(settings, "session_secret", "test-secret")

    app = FastAPI()
    app.include_router(auth.router)

    @app.get("/protected", dependencies=[Depends(auth.require_session)])
    def protected():
        return {"status": "ok"}

    return TestClient(app)


def login(client, email="admin@example.com", password="correct-password"):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_login_success_sets_session_cookie(client):
    response = login(client)

    assert response.status_code == 200
    assert auth.SESSION_COOKIE in response.cookies


def test_login_sets_secure_cookie_when_enabled(client, monkeypatch):
    monkeypatch.setattr(settings, "cookie_secure", True)

    response = login(client)

    assert "Secure" in response.headers["set-cookie"]


def test_login_does_not_set_secure_cookie_by_default(client, monkeypatch):
    monkeypatch.setattr(settings, "cookie_secure", False)

    response = login(client)

    assert "Secure" not in response.headers["set-cookie"]


def test_login_wrong_password_returns_401(client):
    response = login(client, password="wrong")

    assert response.status_code == 401
    assert auth.SESSION_COOKIE not in response.cookies


def test_login_wrong_email_returns_401(client):
    response = login(client, email="other@example.com")

    assert response.status_code == 401


def test_protected_route_without_session_returns_401(client):
    response = client.get("/protected")

    assert response.status_code == 401


def test_protected_route_with_session_returns_200(client):
    login(client)

    response = client.get("/protected")

    assert response.status_code == 200


def test_logout_removes_access(client):
    login(client)
    client.post("/auth/logout")
    client.cookies.clear()

    response = client.get("/protected")

    assert response.status_code == 401


def test_forged_session_cookie_returns_401(client):
    client.cookies.set(auth.SESSION_COOKIE, "9999999999.forged-signature")

    response = client.get("/protected")

    assert response.status_code == 401


def test_session_signed_with_other_secret_returns_401(client, monkeypatch):
    login(client)
    monkeypatch.setattr(settings, "session_secret", "rotated-secret")

    response = client.get("/protected")

    assert response.status_code == 401
