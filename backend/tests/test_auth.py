"""Sign in with Google: checking Google's ID token, the session cookie, and the routes it guards.

Google's signing keys are replaced by a key made here, so nothing goes to the network.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fakes import RESUME_TEXT
from jwt.exceptions import PyJWKClientConnectionError

from app.api.dependencies import get_google_token_verifier
from app.api.routes.auth import SESSION_COOKIE
from app.config import settings
from app.main import app
from app.services.google_identity import (
    GoogleTokenVerifier,
    GoogleUnavailable,
    InvalidGoogleToken,
)

CLIENT_ID = "test-client.apps.googleusercontent.com"
SESSION_SECRET = "a-test-session-secret-that-is-long-enough"
GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
SOMEONE_ELSES_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
GOOGLE_KEY_ID = "google-test-key"


def google_token(key=GOOGLE_KEY, key_id=GOOGLE_KEY_ID, **claims) -> str:
    """An ID token like the one Google's sign-in button returns. A claim passed as None is left out."""
    now = int(time.time())
    payload = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "110169484474386276334",
        "email": "ada@example.com",
        "email_verified": True,
        "iat": now,
        "exp": now + 3600,
        **claims,
    }
    payload = {name: value for name, value in payload.items() if value is not None}
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": key_id})


def session_cookie(secret=SESSION_SECRET, **claims) -> str:
    now = int(time.time())
    payload = {"iss": "interview-ready-ai", "sub": "1", "email": "ada@example.com", "iat": now, "exp": now + 60}
    return jwt.encode({**payload, **claims}, secret, algorithm="HS256")


def analyze(client, headers=None):
    return client.post(
        "/api/analysis", json={"job_text": "We are hiring.", "resume_text": RESUME_TEXT}, headers=headers or {}
    )


def sign_in(client, token):
    return client.post("/api/auth/google", json={"credential": token})


@pytest.fixture
def google(client, monkeypatch) -> None:
    """Turn on Google sign-in, with Google's keys swapped for GOOGLE_KEY."""
    monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "session_secret", SESSION_SECRET)
    monkeypatch.setattr(settings, "app_env", "local")
    verifier = GoogleTokenVerifier(signing_key_for=lambda token: GOOGLE_KEY.public_key())
    monkeypatch.setitem(app.dependency_overrides, get_google_token_verifier, lambda: verifier)


def test_without_a_client_id_everything_is_open(client):
    assert client.get("/api/auth").json() == {"sign_in_required": False, "google_client_id": None, "email": None}
    assert analyze(client).status_code == 200
    assert sign_in(client, google_token()).status_code == 404


def test_with_a_client_id_api_calls_need_a_sign_in(client, google):
    assert client.get("/api/auth").json() == {"sign_in_required": True, "google_client_id": CLIENT_ID, "email": None}
    assert client.get("/api/health").status_code == 200

    refused = analyze(client)
    assert refused.status_code == 401
    assert refused.json()["detail"] == "Sign in with Google to continue."
    assert client.get("/api/report/anything").status_code == 401


def test_a_valid_google_token_signs_in(client, google):
    response = sign_in(client, google_token())

    assert response.status_code == 200
    assert response.json() == {"sign_in_required": True, "google_client_id": CLIENT_ID, "email": "ada@example.com"}
    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    for attribute in ("httponly", "path=/api", "samesite=lax", "max-age=604800"):
        assert attribute in cookie
    assert "secure" not in cookie  # local development runs over plain http

    # The browser now sends the cookie with every call.
    assert client.get("/api/auth").json()["email"] == "ada@example.com"
    assert analyze(client).status_code == 200


def test_the_session_cookie_is_secure_outside_local_development(client, google, monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")

    response = sign_in(client, google_token())

    assert response.status_code == 200
    assert "secure" in response.headers["set-cookie"].lower()


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(google_token(key=SOMEONE_ELSES_KEY), id="not signed by Google"),
        pytest.param(google_token(aud="another-app.apps.googleusercontent.com"), id="for another app"),
        pytest.param(google_token(iss="https://evil.example.com"), id="not issued by Google"),
        pytest.param(google_token(iat=int(time.time()) - 7200, exp=int(time.time()) - 3600), id="expired"),
        pytest.param(google_token(sub=None), id="no account ID"),
        pytest.param(google_token()[:-4] + "AAAA", id="tampered signature"),
        pytest.param("not-a-token", id="not a JWT"),
        pytest.param(jwt.encode({"aud": CLIENT_ID}, SESSION_SECRET, algorithm="HS256"), id="HMAC instead of RSA"),
    ],
)
def test_an_invalid_google_token_is_refused(client, google, token):
    response = sign_in(client, token)

    assert response.status_code == 401
    assert response.json()["detail"] == "The Google sign-in could not be verified. Please try again."
    assert "set-cookie" not in response.headers
    assert analyze(client).status_code == 401


def test_an_account_with_an_unverified_email_is_not_allowed(client, google):
    response = sign_in(client, google_token(email_verified=False))

    assert response.status_code == 403
    assert "not verified" in response.json()["detail"]
    assert "set-cookie" not in response.headers
    assert analyze(client).status_code == 401


def test_google_being_unreachable_is_reported_as_such(client, google, monkeypatch):
    def unreachable(token):
        raise PyJWKClientConnectionError("network is down")

    verifier = GoogleTokenVerifier(signing_key_for=unreachable)
    monkeypatch.setitem(app.dependency_overrides, get_google_token_verifier, lambda: verifier)

    response = sign_in(client, google_token())

    assert response.status_code == 503
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize(
    "cookie",
    [
        pytest.param(session_cookie(secret="someone-elses-secret-that-is-long-enough"), id="forged"),
        pytest.param(session_cookie(iat=int(time.time()) - 120, exp=int(time.time()) - 60), id="expired"),
        pytest.param(session_cookie(iss="somewhere-else"), id="from another issuer"),
        pytest.param(google_token(), id="a Google token instead of a session"),
    ],
)
def test_a_bad_session_cookie_is_refused(client, google, cookie):
    headers = {"Cookie": f"{SESSION_COOKIE}={cookie}"}

    assert analyze(client, headers).status_code == 401
    assert client.get("/api/auth", headers=headers).json()["email"] is None


def test_a_good_session_cookie_is_accepted(client, google):
    assert analyze(client, {"Cookie": f"{SESSION_COOKIE}={session_cookie()}"}).status_code == 200


def test_sign_out_ends_the_session(client, google):
    assert sign_in(client, google_token()).status_code == 200
    assert analyze(client).status_code == 200

    response = client.post("/api/auth/sign-out")

    assert response.status_code == 200
    assert response.json()["email"] is None
    assert analyze(client).status_code == 401


def test_a_refused_call_still_carries_cors_headers(client, google):
    response = client.get("/api/report/anything", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


class TestFetchingGoogleKeys:
    """The verifier's own key lookup, with Google's published key set served from memory."""

    @pytest.fixture(autouse=True)
    def google_key_set(self, monkeypatch):
        public_key = jwt.algorithms.RSAAlgorithm.to_jwk(GOOGLE_KEY.public_key(), as_dict=True)
        key_set = {"keys": [{**public_key, "kid": GOOGLE_KEY_ID, "use": "sig", "alg": "RS256"}]}
        monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", lambda self: key_set)

    def test_a_token_signed_with_a_published_key_is_accepted(self):
        identity = GoogleTokenVerifier().verify(google_token(), CLIENT_ID)

        assert identity.subject == "110169484474386276334"
        assert identity.email == "ada@example.com"
        assert identity.email_verified is True

    def test_a_token_naming_an_unpublished_key_is_refused(self):
        with pytest.raises(InvalidGoogleToken):
            GoogleTokenVerifier().verify(google_token(key=SOMEONE_ELSES_KEY, key_id="unknown"), CLIENT_ID)

    def test_a_failed_key_fetch_means_google_is_unavailable(self, monkeypatch):
        def fail(self):
            raise PyJWKClientConnectionError("network is down")

        monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fail)

        with pytest.raises(GoogleUnavailable):
            GoogleTokenVerifier().verify(google_token(), CLIENT_ID)
