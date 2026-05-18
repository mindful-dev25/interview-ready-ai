import json
import re
from typing import Any

from app.core.llm import GroqLLMClient, LLMMalformedResponseError, LLMGenerationError
from app.schemas import (
    CitationGuardrailResult,
    GuardrailClaim,
    TruthfulnessGuardrailResult,
)


class GuardrailService:
    """Guardrail checks for answer truthfulness, citation quality, and safety."""

    SENSITIVE_PATTERNS = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{3}[ .-]?\d{2}[ .-]?\d{4}\b",  # SSN alternate
        r"\b\d{3}[ .-]?\d{3}[ .-]?\d{4}\b",  # phone number
        r"\b\w+@\w+\.\w+\b",  # email
        r"\b\$\d+[\d,]*\b",  # salary
        r"\b(salary|compensation|pay|bank account|credit card)\b",
        r"\b(confidential|proprietary|secret|private data)\b",
    ]

    EXAGGERATION_TERMS = [
        "senior",
        "lead",
        "principal",
        "expert",
        "architect",
        "owned",
        "directed",
        "managed a team",
        "head of",
        "drove",
        "pioneered",
        "championed",
    ]

    EXAMPLE_TRIGGERS = [
        "for example",
        "for instance",
        "during",
        "while",
        "when",
        "as part of",
        "in a project",
        "on a project",
        "with a team",
        "resulting in",
        "resulted in",
        "improved",
        "reduced",
        "increased",
        "delivered",
        "launched",
        "built",
    ]

    ASSERTION_TERMS = [
        "led",
        "built",
        "designed",
        "developed",
        "owned",
        "implemented",
        "managed",
        "improved",
        "delivered",
        "reduced",
        "increased",
        "created",
    ]

    def __init__(self, llm_client: GroqLLMClient | None = None) -> None:
        self.llm = llm_client or GroqLLMClient()

    async def review_answer(
        self,
        answer: str,
        evidence: list[dict[str, Any]],
        resume_text: str | None = None,
    ) -> dict[str, Any]:
        answer_text = answer.strip()
        evidence_ids = self._extract_evidence_ids(answer_text)
        truthfulness_result = self._evaluate_truthfulness(
            answer_text, evidence, evidence_ids, resume_text
        )
        citation_result = self._evaluate_citations(
            answer_text, evidence, evidence_ids
        )
        suggested_safe_rewrite = await self._generate_safe_rewrite(
            answer_text, evidence, truthfulness_result, citation_result
        )

        return {
            "truthfulness_result": truthfulness_result,
            "citation_result": citation_result,
            "unsupported_claims": truthfulness_result.unsupported_claims,
            "suggested_safe_rewrite": suggested_safe_rewrite,
        }

    def _extract_evidence_ids(self, text: str) -> list[str]:
        return list({match.group(1).strip() for match in re.finditer(r"\[([^\]]+)\]", text)})

    def _split_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def _evaluate_citations(
        self,
        answer: str,
        evidence: list[dict[str, Any]],
        cited_ids: list[str],
    ) -> CitationGuardrailResult:
        available_ids = {item.get("id") for item in evidence if item.get("id")}
        valid_cited_ids = [cid for cid in cited_ids if cid in available_ids]
        invalid_ids = [cid for cid in cited_ids if cid and cid not in available_ids]
        missing_citations = self._find_missing_citation_claims(answer, cited_ids)

        notes: list[str] = []
        if invalid_ids:
            notes.append(
                "Some citations refer to evidence IDs that were not found in the retrieved context."
            )
        if not valid_cited_ids:
            notes.append(
                "No supported evidence IDs were cited in the answer."
            )
        if missing_citations:
            notes.append(
                "Some claims appear unsupported because they lack explicit evidence citations."
            )

        passed = not missing_citations and bool(valid_cited_ids)
        summary = (
            "Citations are present and match retrieved evidence."
            if passed
            else "Citation coverage is incomplete or unsupported evidence IDs were cited."
        )

        return CitationGuardrailResult(
            passed=passed,
            summary=summary,
            cited_evidence_ids=valid_cited_ids,
            missing_citation_claims=missing_citations,
            weak_citation_notes=notes,
        )

    def _evaluate_truthfulness(
        self,
        answer: str,
        evidence: list[dict[str, Any]],
        cited_ids: list[str],
        resume_text: str | None = None,
    ) -> TruthfulnessGuardrailResult:
        claims: list[GuardrailClaim] = []
        sentences = self._split_sentences(answer)
        resume_evidence_ids = {
            item.get("id")
            for item in evidence
            if item.get("source_type") == "resume" and item.get("id")
        }
        resume_text_lower = resume_text.lower() if resume_text else ""

        missing_citation_sentences = self._find_missing_citation_claims(answer, cited_ids)
        for sentence in missing_citation_sentences:
            claims.append(
                GuardrailClaim(
                    claim=sentence,
                    supported=False,
                    evidence_ids=[],
                    explanation="This claim appears to be factual or personal but lacks a source citation.",
                    severity="high",
                    suggested_fix="Cite relevant evidence or make the statement clearly subjective.",
                )
            )

        for sentence in sentences:
            private_issues = self._find_sensitive_information(sentence)
            if private_issues:
                claims.extend(private_issues)

            exaggeration = self._find_exaggeration(sentence, cited_ids, reset=False)
            if exaggeration:
                claims.extend(exaggeration)

            if self._claim_not_found_in_resume(
                sentence, evidence, resume_evidence_ids, resume_text_lower
            ):
                claims.append(
                    GuardrailClaim(
                        claim=sentence,
                        supported=False,
                        evidence_ids=[],
                        explanation="This personal claim is not supported by the resume evidence.",
                        severity="high",
                        suggested_fix="Keep the answer grounded in documented resume achievements.",
                    )
                )

        vague_claim = self._find_vague_answer(answer)
        if vague_claim:
            claims.append(vague_claim)

        score = round(max(0.0, 1.0 - len(claims) * 0.15), 2)
        passed = len(claims) == 0
        summary = (
            "The answer is grounded, cites evidence, and does not contain risky claims."
            if passed
            else "The answer contains one or more truthfulness or clarity issues that should be reviewed."
        )

        return TruthfulnessGuardrailResult(
            passed=passed,
            score=score,
            summary=summary,
            claims=claims,
            unsupported_claims=claims,
        )

    def _find_missing_citation_claims(
        self,
        answer: str,
        cited_ids: list[str],
    ) -> list[str]:
        sentences = self._split_sentences(answer)
        missing: list[str] = []
        cited_in_answer = bool(cited_ids)

        for sentence in sentences:
            lower = sentence.lower()
            has_assertion = any(term in lower for term in self.ASSERTION_TERMS)
            has_personal_reference = bool(re.search(r"\b(i|my|we|our|me)\b", lower))
            has_citation = bool(re.search(r"\[[^\]]+\]", sentence))

            if has_assertion and has_personal_reference and not has_citation:
                missing.append(sentence)
            elif not cited_in_answer and has_assertion and len(sentence) > 40:
                missing.append(sentence)

        return missing

    def _find_sensitive_information(self, text: str) -> list[GuardrailClaim]:
        findings: list[GuardrailClaim] = []
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                findings.append(
                    GuardrailClaim(
                        claim=text,
                        supported=False,
                        evidence_ids=[],
                        explanation="The answer contains private or sensitive information that should not be shared.",
                        severity="high",
                        suggested_fix="Remove personal identifiers and sensitive details from the response.",
                    )
                )
                break
        return findings

    def _find_exaggeration(
        self,
        sentence: str,
        cited_ids: list[str],
        reset: bool = True,
    ) -> list[GuardrailClaim]:
        findings: list[GuardrailClaim] = []
        lower = sentence.lower()
        if any(term in lower for term in self.EXAGGERATION_TERMS):
            cited = bool(re.search(r"\[[^\]]+\]", sentence))
            explanation = (
                "This sentence may overstate seniority or responsibility."
                if cited
                else "This sentence may exaggerate responsibilities without clear evidence."
            )
            findings.append(
                GuardrailClaim(
                    claim=sentence,
                    supported=cited,
                    evidence_ids=self._extract_evidence_ids(sentence) if cited else [],
                    explanation=explanation,
                    severity="medium",
                    suggested_fix="Use more measured language and align it with documented evidence.",
                )
            )
        return findings

    def _claim_not_found_in_resume(
        self,
        sentence: str,
        evidence: list[dict[str, Any]],
        resume_evidence_ids: set[str],
        resume_text_lower: str,
    ) -> bool:
        lower = sentence.lower()
        if not re.search(r"\b(i|my|we|our|me)\b", lower):
            return False
        if not any(term in lower for term in self.ASSERTION_TERMS):
            return False

        sentence_ids = set(self._extract_evidence_ids(sentence))
        if sentence_ids & resume_evidence_ids:
            return False

        if resume_text_lower and any(word in resume_text_lower for word in re.findall(r"\b\w{4,}\b", sentence.lower())):
            return False

        return True

    def _find_vague_answer(self, answer: str) -> GuardrailClaim | None:
        lower = answer.lower()
        if len(answer) < 80:
            return None
        if any(trigger in lower for trigger in self.EXAMPLE_TRIGGERS):
            return None
        if re.search(r"\b(for example|for instance|during|when|while|as part of)\b", lower):
            return None

        return GuardrailClaim(
            claim=answer,
            supported=False,
            evidence_ids=[],
            explanation="The answer is generic and lacks concrete examples or measurable results.",
            severity="medium",
            suggested_fix="Add a specific example with evidence-backed results to make the answer more persuasive.",
        )

    async def _generate_safe_rewrite(
        self,
        answer: str,
        truthfulness: TruthfulnessGuardrailResult,
        citation: CitationGuardrailResult,
    ) -> str | None:
        if truthfulness.passed and citation.passed:
            return None

        prompt = self._build_rewrite_prompt(answer, truthfulness, citation)
        try:
            response = await self.llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a guardrail reviewer. Rewrite the answer to remove unsupported claims, "
                    "exaggerated seniority, sensitive information, and vague language while preserving the core meaning. "
                    "Cite evidence only when the source is explicitly available."
                ),
            )
            return response.strip()
        except (LLMMalformedResponseError, LLMGenerationError, ValueError):
            return self._build_fallback_rewrite(answer, truthfulness, citation)

    def _build_rewrite_prompt(
        self,
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

    def _build_fallback_rewrite(
        self,
        answer: str,
        truthfulness: TruthfulnessGuardrailResult,
        citation: CitationGuardrailResult,
    ) -> str:
        rewrite = answer
        if truthfulness.unsupported_claims:
            rewrite = re.sub(r"\[[^\]]+\]", "", rewrite).strip()
        if citation.missing_citation_claims:
            rewrite += " This response stays close to documented evidence and avoids unsupported details."
        return rewrite
