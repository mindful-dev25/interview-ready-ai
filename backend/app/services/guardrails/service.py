from typing import Any

from app.core.llm import GroqLLMClient
from app.services.guardrails.checks import evaluate_citations, evaluate_truthfulness
from app.services.guardrails.detectors import find_missing_citation_claims
from app.services.guardrails.rewrite import SafeRewriter
from app.services.guardrails.text import extract_evidence_ids


class GuardrailService:
    """Runs truthfulness and citation checks on an answer and suggests a safe rewrite."""

    def __init__(self, llm_client: GroqLLMClient | None = None) -> None:
        self.llm = llm_client or GroqLLMClient()
        self.rewriter = SafeRewriter(self.llm)

    async def review_answer(
        self,
        answer: str,
        evidence: list[dict[str, Any]],
        resume_text: str | None = None,
    ) -> dict[str, Any]:
        answer_text = answer.strip()
        cited_ids = extract_evidence_ids(answer_text)
        missing_citations = find_missing_citation_claims(answer_text, cited_ids)

        truthfulness_result = evaluate_truthfulness(
            answer_text, evidence, missing_citations, resume_text
        )
        citation_result = evaluate_citations(evidence, cited_ids, missing_citations)
        suggested_safe_rewrite = await self.rewriter.rewrite(
            answer_text, truthfulness_result, citation_result
        )

        return {
            "truthfulness_result": truthfulness_result,
            "citation_result": citation_result,
            "unsupported_claims": truthfulness_result.unsupported_claims,
            "suggested_safe_rewrite": suggested_safe_rewrite,
        }
