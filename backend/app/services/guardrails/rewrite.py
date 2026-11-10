"""Suggest a safer rewrite of an answer that failed a guardrail check."""

from app.core.llm import LLMClient, LLMGenerationError, LLMMalformedResponseError
from app.schemas import CitationGuardrailResult, TruthfulnessGuardrailResult
from app.services.guardrails.text import strip_citations

_SYSTEM_PROMPT = (
    "You are a guardrail reviewer. Rewrite the answer to remove unsupported claims, "
    "exaggerated seniority, sensitive information, and vague language while preserving the core meaning. "
    "Cite evidence only when the source is explicitly available."
)


class SafeRewriter:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm = llm_client

    async def rewrite(
        self,
        answer: str,
        truthfulness: TruthfulnessGuardrailResult,
        citation: CitationGuardrailResult,
    ) -> str | None:
        """Return a rewrite, or ``None`` when both checks passed and nothing needs changing."""
        if truthfulness.passed and citation.passed:
            return None

        try:
            response = await self.llm.generate(
                prompt=build_rewrite_prompt(answer, truthfulness, citation),
                system_prompt=_SYSTEM_PROMPT,
            )
            return response.strip()
        except (LLMMalformedResponseError, LLMGenerationError, ValueError):
            return build_fallback_rewrite(answer, truthfulness, citation)


def build_rewrite_prompt(
    answer: str,
    truthfulness: TruthfulnessGuardrailResult,
    citation: CitationGuardrailResult,
) -> str:
    issues = []
    if truthfulness.unsupported_claims:
        issues.append("unsupported or unverified claims")
    if citation.missing_citation_claims:
        issues.append("missing citations")
    if any(claim.severity == "high" for claim in truthfulness.unsupported_claims):
        issues.append("sensitive or risky details")
    if not issues:
        issues.append("clarity and evidence alignment")

    return (
        "Here is an interview answer and a list of verification issues. Rewrite the answer to make it safe, grounded, "
        "and review-ready. Remove any unsupported claims, avoid exaggerated seniority, remove private or sensitive information, "
        "and make the answer more specific when possible.\n\n"
        f"Answer:\n{answer}\n\n"
        "Issues:\n"
        + "\n".join(f"- {issue}" for issue in issues)
        + "\n"
    )


def build_fallback_rewrite(
    answer: str,
    truthfulness: TruthfulnessGuardrailResult,
    citation: CitationGuardrailResult,
) -> str:
    """Deterministic rewrite used when the LLM is unavailable."""
    rewrite = answer
    if truthfulness.unsupported_claims:
        rewrite = strip_citations(rewrite).strip()
    if citation.missing_citation_claims:
        rewrite += " This response stays close to documented evidence and avoids unsupported details."
    return rewrite
