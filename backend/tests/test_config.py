import os
from app.config import get_settings


def test_get_settings_loads_groq_values(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("GROQ_CHAT_MODEL", "test-model")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.groq_api_key == "test-key"
    assert settings.groq_base_url == "https://api.groq.com/openai/v1"
    assert settings.groq_chat_model == "test-model"

    get_settings.cache_clear()
