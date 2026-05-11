from typing import Any

import httpx

from app.config import settings


class LLMConfigurationError(RuntimeError):
    """Raised when LLM generation is requested without required config."""


class GroqLLMClient:
    """Small OpenAI-compatible chat adapter for Groq."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = settings.groq_api_key if api_key is None else api_key
        configured_base_url = settings.groq_base_url if base_url is None else base_url
        self.base_url = configured_base_url.rstrip("/")
        self.model = settings.groq_chat_model if model is None else model
        self.timeout = timeout

    async def generate(self, prompt: str) -> str:
        api_key, base_url, model = self._validated_config()
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                "Groq chat completion response did not include generated content."
            ) from exc

        if not isinstance(content, str):
            raise RuntimeError(
                "Groq chat completion response content was not a string."
            )
        return content

    def _validated_config(self) -> tuple[str, str, str]:
        api_key = self.api_key.strip()
        base_url = self.base_url.strip()
        model = self.model.strip()

        if not api_key:
            raise LLMConfigurationError(
                "GROQ_API_KEY is required for LLM generation. Set it in backend/.env."
            )
        if not base_url:
            raise LLMConfigurationError(
                "GROQ_BASE_URL is required for LLM generation. Set it in backend/.env."
            )
        if not model:
            raise LLMConfigurationError(
                "GROQ_CHAT_MODEL is required for LLM generation. Set it in backend/.env."
            )

        return api_key, base_url, model


LocalLLMClient = GroqLLMClient
