import base64
import hashlib
import hmac
import secrets
import time

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel

from app.config import settings

SESSION_COOKIE = "session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60

router = APIRouter(prefix="/auth")


class LoginRequest(BaseModel):
    email: str
    password: str


def _sign(payload: str) -> str:
    digest = hmac.new(
        settings.session_secret.encode(), payload.encode(), hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _make_token() -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = str(expires_at)
    return f"{payload}.{_sign(payload)}"


def _is_valid_token(token: str | None) -> bool:
    if not token or not settings.session_secret:
        return False
    payload, _, signature = token.partition(".")
    if not payload or not signature:
        return False
    if not hmac.compare_digest(signature, _sign(payload)):
        return False
    try:
        expires_at = int(payload)
    except ValueError:
        return False
    return expires_at > time.time()


def require_session(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> None:
    if not _is_valid_token(session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )


@router.post("/login")
def login(body: LoginRequest, response: Response):
    email_ok = secrets.compare_digest(
        body.email.encode(), settings.admin_email.encode()
    )
    password_ok = secrets.compare_digest(
        body.password.encode(), settings.admin_password.encode()
    )
    configured = (
        settings.admin_email and settings.admin_password and settings.session_secret
    )
    if not (email_ok and password_ok and configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=_make_token(),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return {"status": "ok"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return {"status": "ok"}
