"""Small helpers for URLs that come from users and from LLM output."""

import re

from pydantic import HttpUrl, TypeAdapter

_http_url_adapter = TypeAdapter(HttpUrl)
_HAS_SCHEME = re.compile(r"^https?://", re.IGNORECASE)


def normalize_job_url(raw: str) -> str:
    """Trim the URL and add https:// when the scheme was left out."""
    url = raw.strip()
    if url and not _HAS_SCHEME.match(url):
        url = f"https://{url}"
    return url


def safe_url(raw: str) -> HttpUrl | None:
    """Return the URL if it is a valid http(s) URL, otherwise None."""
    if not raw or not raw.strip():
        return None
    try:
        return _http_url_adapter.validate_python(raw.strip())
    except Exception:
        return None
