import asyncio
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Transient failures worth retrying: rate limiting and upstream hiccups.
_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
_MAX_ATTEMPTS = 3
_MAX_RETRY_DELAY_SECONDS = 10.0


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
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = settings.groq_api_key if api_key is None else api_key
        configured_base_url = settings.groq_base_url if base_url is None else base_url
        self.base_url = configured_base_url.rstrip("/")
        self.model = settings.groq_chat_model if model is None else model
        self.timeout = timeout
        self._transport = transport  # lets tests substitute a fake HTTP layer
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None

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
        url = f"{base_url}/chat/completions"

        attempt = 1
        while True:
            try:
                response = await self._http_client().post(url, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError(
                    f"Groq request timed out after {self.timeout} seconds."
                ) from exc
            except httpx.RequestError as exc:
                raise LLMGenerationError(f"Groq request failed: {exc}") from exc

            if response.status_code in _RETRYABLE_STATUS_CODES and attempt < _MAX_ATTEMPTS:
                delay = self._retry_delay(response, attempt)
                logger.warning(
                    "Groq returned %s; retrying in %.1fs (attempt %d of %d).",
                    response.status_code, delay, attempt, _MAX_ATTEMPTS,
                )
                await asyncio.sleep(delay)
                attempt += 1
                continue

            if response.is_error:
                raise self._status_error(response)
            return self._parse_text_response(response)

    async def aclose(self) -> None:
        """Close the pooled HTTP connection, if one was opened."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None
        self._client_loop = None

    def _http_client(self) -> httpx.AsyncClient:
        """Return a pooled client so calls reuse one connection instead of a new TLS handshake each.

        An httpx client is tied to the event loop it was created on, so a new one
        is made if the loop changed (as happens between test runs).
        """
        loop = asyncio.get_running_loop()
        if self._client is None or self._client.is_closed or self._client_loop is not loop:
            self._client = httpx.AsyncClient(timeout=self.timeout, transport=self._transport)
            self._client_loop = loop
        return self._client

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        """Honor the server's Retry-After when given, otherwise back off exponentially."""
        try:
            delay = float(response.headers.get("retry-after", ""))
        except ValueError:
            delay = float(2 ** (attempt - 1))
        return min(max(delay, 0.0), _MAX_RETRY_DELAY_SECONDS)

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
