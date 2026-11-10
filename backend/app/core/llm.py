import asyncio
import logging
from typing import Any

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# Covers the model's thinking plus the longest reply the app asks for (the final report).
_MAX_OUTPUT_TOKENS = 16_000
# When a safety classifier declines a request, the API re-runs it on the model
# Anthropic recommends for that case instead of returning the refusal.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMConfigurationError(RuntimeError):
    """Raised when LLM generation is requested without required config."""


class LLMGenerationError(RuntimeError):
    """Raised when an LLM request fails."""


class LLMAuthenticationError(LLMGenerationError):
    """Raised when the Claude API rejects the API key."""


class LLMRateLimitError(LLMGenerationError):
    """Raised when the Claude API is still rate limiting after the SDK's retries."""


class LLMTimeoutError(LLMGenerationError):
    """Raised when the Claude API does not respond before the timeout."""


class LLMMalformedResponseError(LLMGenerationError):
    """Raised when a reply has no usable text or is not in the expected format."""


class LLMClient:
    """Text-in, text-out adapter for the Claude Messages API.

    The Anthropic SDK pools connections and retries rate limits, server errors
    and connection failures itself, so this class only maps configuration,
    replies and errors onto what the services expect.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 2,
        http_client: anthropic.DefaultAsyncHttpxClient | None = None,
    ) -> None:
        self.api_key = settings.anthropic_api_key if api_key is None else api_key
        self.model = settings.claude_model if model is None else model
        self.timeout = timeout
        self.max_retries = max_retries
        self._http_client = http_client  # lets tests substitute a fake HTTP layer
        self._client: anthropic.AsyncAnthropic | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        api_key, model = self._validated_config()
        user_content = prompt.strip()
        if not user_content:
            raise ValueError("Prompt must not be empty.")

        request: dict[str, Any] = {
            "model": model,
            "max_tokens": _MAX_OUTPUT_TOKENS,
            "messages": [{"role": "user", "content": user_content}],
            "betas": [_FALLBACK_BETA],
            "fallbacks": "default",
        }
        system_content = (system_prompt or "").strip()
        if system_content:
            request["system"] = system_content

        try:
            response = await self._sdk_client(api_key).beta.messages.create(**request)
        except anthropic.APITimeoutError as exc:
            raise LLMTimeoutError(
                f"Claude request timed out after {self.timeout} seconds."
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMGenerationError(f"Claude request failed: {exc}") from exc
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise LLMAuthenticationError(
                f"Claude authentication failed ({exc.status_code}): {exc.message}"
            ) from exc
        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError(f"Claude rate limit exceeded: {exc.message}") from exc
        except anthropic.APIStatusError as exc:
            raise LLMGenerationError(
                f"Claude request failed ({exc.status_code}): {exc.message}"
            ) from exc

        return self._text_from(response)

    async def aclose(self) -> None:
        """Close the pooled HTTP connections, if any were opened."""
        if self._client is not None:
            await self._client.close()
        self._client = None
        self._client_loop = None

    def _sdk_client(self, api_key: str) -> anthropic.AsyncAnthropic:
        """Return one shared SDK client so calls reuse its connection pool.

        The pool is tied to the event loop it was created on, so a new client
        is made if the loop changed (as happens between test runs).
        """
        loop = asyncio.get_running_loop()
        if self._client is None or self._client_loop is not loop:
            self._client = anthropic.AsyncAnthropic(
                api_key=api_key,
                timeout=self.timeout,
                max_retries=self.max_retries,
                http_client=self._http_client,
            )
            self._client_loop = loop
        return self._client

    @staticmethod
    def _text_from(response: Any) -> str:
        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            reason = f" (category: {category})" if category else ""
            raise LLMGenerationError(f"Claude declined this request{reason}.")

        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise LLMMalformedResponseError("Claude's reply did not include any text.")
        if response.stop_reason == "max_tokens":
            logger.warning("Claude's reply was cut off at the %d-token output limit.", _MAX_OUTPUT_TOKENS)
        return text

    def _validated_config(self) -> tuple[str, str]:
        api_key = self.api_key.strip()
        model = self.model.strip()

        if not api_key:
            raise LLMConfigurationError(
                "ANTHROPIC_API_KEY is required for LLM generation. Set it in backend/.env."
            )
        if not model:
            raise LLMConfigurationError(
                "CLAUDE_MODEL must not be empty. Set it in backend/.env or remove it to use the default."
            )

        return api_key, model
