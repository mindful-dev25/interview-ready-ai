from app.config import settings


class LocalLLMClient:
    """Placeholder adapter for Ollama-backed local model calls."""

    def __init__(
        self,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_chat_model,
    ) -> None:
        self.base_url = base_url
        self.model = model

    async def generate(self, prompt: str) -> str:
        # TODO: Replace with langchain-ollama or direct Ollama API invocation.
        return f"[TODO: generate with {self.model}] {prompt[:120]}"
