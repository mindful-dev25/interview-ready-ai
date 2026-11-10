"""Test doubles shared across the test suite. Nothing here touches the network."""


class FakeLLM:
    """Stands in for LLMClient: returns a canned reply and records the prompts it was given."""

    def __init__(self, reply: str = "ok") -> None:
        self.reply = reply
        self.prompts: list[str] = []

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        self.prompts.append(prompt)
        return self.reply
