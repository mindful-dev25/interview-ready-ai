from app.config import get_settings


def test_get_settings_loads_claude_values(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("CLAUDE_MODEL", "test-model")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.anthropic_api_key == "test-key"
    assert settings.claude_model == "test-model"

    get_settings.cache_clear()
