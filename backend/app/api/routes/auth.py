"""Sign in with Google, switched on by setting GOOGLE_CLIENT_ID.

The frontend asks ``GET /auth`` whether sign-in is needed and for the OAuth client ID that Google's
button needs. When someone signs in, the button gives the browser a Google ID token, which the
frontend posts to ``POST /auth/google``. The token is verified here, on the server. If it is
valid and the account may use the app, the response sets a session cookie, which the browser then
sends with every other call. ``POST /auth/sign-out`` clears the cookie.
"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.api.dependencies import get_google_token_verifier
from app.config import settings
from app.schemas import AuthStatusResponse, GoogleSignInRequest
from app.services.google_identity import GoogleIdentity, GoogleTokenVerifier, GoogleUnavailable, InvalidGoogleToken

SESSION_COOKIE = "irai_session"
# The cookie is only needed by the API, which is under /api both locally and in the one-container image.
SESSION_COOKIE_PATH = "/api"
SESSION_LIFETIME = timedelta(days=7)
SESSION_ISSUER = "interview-ready-ai"

# Used when SESSION_SECRET is not set: sessions then end whenever the server restarts.
_fallback_session_secret = secrets.token_urlsafe(32)

router = APIRouter(prefix="/auth", tags=["auth"])


def may_sign_in(identity: GoogleIdentity) -> bool:
    """The access rule: any Google account whose email address Google has verified."""
    return identity.email_verified


def _session_secret() -> str:
    return settings.session_secret or _fallback_session_secret


def _session_token(identity: GoogleIdentity) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "iss": SESSION_ISSUER,
        "sub": identity.subject,
        "email": identity.email,
        "iat": now,
        "exp": now + SESSION_LIFETIME,
    }
    return jwt.encode(claims, _session_secret(), algorithm="HS256")


def signed_in_email(session: str | None) -> str | None:
    """The email in a valid, unexpired session cookie, or None when there is no such cookie."""
    if not session:
        return None
    try:
        claims = jwt.decode(
            session,
            _session_secret(),
            algorithms=["HS256"],
            issuer=SESSION_ISSUER,
            options={"require": ["iss", "sub", "exp"]},
        )
    except jwt.PyJWTError:
        return None
    return str(claims.get("email") or "")


def _cookie_is_secure() -> bool:
    # Local development runs over plain http; everywhere else the site is served over https.
    return settings.app_env != "local"


def _status(email: str | None) -> AuthStatusResponse:
    client_id = settings.google_client_id
    return AuthStatusResponse(sign_in_required=bool(client_id), google_client_id=client_id or None, email=email)


async def require_sign_in(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> None:
    if settings.google_client_id and signed_in_email(session) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in with Google to continue.")


@router.get("", response_model=AuthStatusResponse)
async def auth_status(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> AuthStatusResponse:
    return _status(signed_in_email(session))


# A plain function, so FastAPI runs it in a worker thread: checking the token can fetch Google's keys.
@router.post("/google", response_model=AuthStatusResponse)
def sign_in_with_google(
    payload: GoogleSignInRequest,
    response: Response,
    verifier: GoogleTokenVerifier = Depends(get_google_token_verifier),
) -> AuthStatusResponse:
    client_id = settings.google_client_id
    if not client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Google sign-in is not set up on this server.")

    try:
        identity = verifier.verify(payload.credential, client_id)
    except GoogleUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reach Google to check the sign-in. Please try again.",
        ) from None
    except InvalidGoogleToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Google sign-in could not be verified. Please try again.",
        ) from None

    if not may_sign_in(identity):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Google account's email address is not verified, so it cannot be used to sign in.",
        )

    response.set_cookie(
        SESSION_COOKIE,
        _session_token(identity),
        max_age=int(SESSION_LIFETIME.total_seconds()),
        path=SESSION_COOKIE_PATH,
        secure=_cookie_is_secure(),
        httponly=True,
        samesite="lax",
    )
    return _status(identity.email)


@router.post("/sign-out", response_model=AuthStatusResponse)
async def sign_out(response: Response) -> AuthStatusResponse:
    response.delete_cookie(
        SESSION_COOKIE, path=SESSION_COOKIE_PATH, secure=_cookie_is_secure(), httponly=True, samesite="lax"
    )
    return _status(None)
