class GuardrailService:
    """Placeholder guardrail checks for interview answer quality and safety."""

    async def review_answer(self, answer: str, evidence: list[dict[str, str]]) -> list[str]:
        # TODO: Detect unsupported claims, overstatement, hallucination, and privacy issues.
        _ = (answer, evidence)
        return []
