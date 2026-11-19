"""The optional APP_PASSWORD gate."""

import pytest
from fakes import RESUME_TEXT

from app.config import settings


@pytest.fixture
def password(monkeypatch) -> str:
    monkeypatch.setattr(settings, "app_password", "open sesame")
    return "open sesame"


def analyze(client, headers=None):
    return client.post(
        "/api/analysis", json={"job_text": "We are hiring.", "resume_text": RESUME_TEXT}, headers=headers or {}
    )


def test_without_a_password_everything_is_open(client, monkeypatch):
    monkeypatch.setattr(settings, "app_password", "")

    assert client.get("/api/auth").json() == {"password_required": False}
    assert client.post("/api/auth", json={"password": "anything"}).status_code == 200
    assert analyze(client).status_code == 200


def test_with_a_password_api_calls_need_it(client, password):
    assert client.get("/api/auth").json() == {"password_required": True}
    assert client.get("/api/health").status_code == 200

    missing = analyze(client)
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Enter the app password to continue."
    assert analyze(client, {"X-App-Password": "wrong"}).status_code == 401
    assert client.get("/api/report/anything").status_code == 401

    assert analyze(client, {"X-App-Password": password}).status_code == 200


def test_password_check(client, password):
    assert client.post("/api/auth", json={"password": password}).status_code == 200
    assert client.post("/api/auth", json={"password": "wrong"}).status_code == 401


def test_a_refused_call_still_carries_cors_headers(client, password):
    response = client.get("/api/report/anything", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
