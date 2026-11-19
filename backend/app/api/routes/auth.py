"""Optional shared password for the whole app, set with APP_PASSWORD.

The frontend asks ``GET /auth`` whether a password is needed, checks what the user types with
``POST /auth``, and then sends it in the ``X-App-Password`` header on every other call.
"""

import hmac

from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.schemas import AuthCheckRequest, AuthStatusResponse

PASSWORD_HEADER = "X-App-Password"

router = APIRouter(prefix="/auth", tags=["auth"])


def password_matches(candidate: str | None) -> bool:
    """True when no password is set, or when ``candidate`` is it (compared in constant time)."""
    expected = settings.app_password
    if not expected:
        return True
    return candidate is not None and hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))


async def require_app_password(
    x_app_password: str | None = Header(default=None, alias=PASSWORD_HEADER),
) -> None:
    if not password_matches(x_app_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Enter the app password to continue.")


@router.get("", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    return AuthStatusResponse(password_required=bool(settings.app_password))


@router.post("", response_model=AuthStatusResponse)
async def check_password(payload: AuthCheckRequest) -> AuthStatusResponse:
    if not password_matches(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="That password is not correct.")
    return AuthStatusResponse(password_required=bool(settings.app_password))
