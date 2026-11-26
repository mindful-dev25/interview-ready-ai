"""Checks the ID tokens that Google's "Sign in with Google" button hands the browser.

An ID token is a JWT signed by Google. It is accepted only when its signature matches one of
Google's published keys, Google issued it for this app's OAuth client ID (``GOOGLE_CLIENT_ID``),
and it has not expired.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jwt
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

GOOGLE_KEYS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
# Allowed difference between Google's clock and this server's when checking the token's times.
CLOCK_SKEW_SECONDS = 60


class InvalidGoogleToken(Exception):
    """The token is not a current Google ID token for this app."""


class GoogleUnavailable(Exception):
    """Google's signing keys could not be fetched, so the token could not be checked."""


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    """Google's permanent ID for the account (the ``sub`` claim). Unlike the email, it never changes."""
    email: str
    email_verified: bool


class GoogleTokenVerifier:
    """Verifies Google ID tokens against Google's public keys.

    ``signing_key_for`` returns the public key that should have signed a token. By default the keys
    are fetched from Google and cached; tests pass their own so nothing goes to the network.
    """

    def __init__(self, signing_key_for: Callable[[str], Any] | None = None) -> None:
        if signing_key_for is None:
            # Google rotates its keys every few days. The client caches them and fetches again
            # when a token names a key it has not seen.
            keys = jwt.PyJWKClient(GOOGLE_KEYS_URL, cache_keys=True, lifespan=3600, timeout=10)
            signing_key_for = lambda token: keys.get_signing_key_from_jwt(token).key  # noqa: E731
        self._signing_key_for = signing_key_for

    def verify(self, token: str, client_id: str) -> GoogleIdentity:
        """Return who the token identifies, or raise ``InvalidGoogleToken`` / ``GoogleUnavailable``.

        This can fetch Google's keys over the network, so call it from a worker thread.
        """
        try:
            claims = jwt.decode(
                token,
                self._signing_key_for(token),
                algorithms=["RS256"],
                audience=client_id,
                issuer=GOOGLE_ISSUERS,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["iss", "aud", "sub", "iat", "exp"]},
            )
        except PyJWKClientConnectionError as error:
            raise GoogleUnavailable(str(error)) from error
        except PyJWTError as error:
            raise InvalidGoogleToken(str(error)) from error

        return GoogleIdentity(
            subject=str(claims["sub"]),
            email=str(claims.get("email") or ""),
            # Google sends a boolean; very old tokens sent the string "true".
            email_verified=claims.get("email_verified") in (True, "true"),
        )
