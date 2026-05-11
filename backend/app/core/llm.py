from typing import Any

import httpx

from app.config import settings


class LLMConfigurationError(RuntimeError):
    """Raised when LLM generation is requested without required config."""


class LLMGenerationError(RuntimeError):
    """Raised when an LLM request fails."""


class LLMAuthenticationError(LLMGenerationError):
    """Raised when Groq rejects the API key."""


class LLMRateLimitError(LLMGenerationError):
    """Raised when Groq rate limits the request."""


class LLMTimeoutError(LLMGenerationError):
    """Raised when Groq does not respond before the timeout."""


class LLMMalformedResponseError(LLMGenerationError):
    """Raised when Groq returns an unexpected response shape."""


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

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        api_key, base_url, model = self._validated_config()
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._build_messages(prompt, system_prompt),
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Groq request timed out after {self.timeout} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise self._status_error(exc.response) from exc
        except httpx.RequestError as exc:
            raise LLMGenerationError(f"Groq request failed: {exc}") from exc

        return self._parse_text_response(response)

    def _build_messages(
        self, prompt: str, system_prompt: str | None
    ) -> list[dict[str, str]]:
        user_content = prompt.strip()
        if not user_content:
            raise ValueError("Prompt must not be empty.")

        messages: list[dict[str, str]] = []
        if system_prompt is not None:
            system_content = system_prompt.strip()
            if system_content:
                messages.append({"role": "system", "content": system_content})

        messages.append({"role": "user", "content": user_content})
        return messages

    def _parse_text_response(self, response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError as exc:
            raise LLMMalformedResponseError(
                "Groq chat completion response was not valid JSON."
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMMalformedResponseError(
                "Groq chat completion response did not include generated content."
            ) from exc

        if not isinstance(content, str):
            raise LLMMalformedResponseError(
                "Groq chat completion response content was not a string."
            )

        text = content.strip()
        if not text:
            raise LLMMalformedResponseError(
                "Groq chat completion response content was empty."
            )
        return text

    def _status_error(self, response: httpx.Response) -> LLMGenerationError:
        detail = self._error_detail(response)
        if response.status_code in {401, 403}:
            return LLMAuthenticationError(
                f"Groq authentication failed ({response.status_code}): {detail}"
            )
        if response.status_code == 429:
            return LLMRateLimitError(f"Groq rate limit exceeded: {detail}")

        return LLMGenerationError(
            f"Groq request failed ({response.status_code}): {detail}"
        )

    def _error_detail(self, response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            text = response.text.strip()
            return text or response.reason_phrase

        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        if isinstance(error, str) and error.strip():
            return error.strip()

        return response.reason_phrase

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
