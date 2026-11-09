"""Combine detector findings into the truthfulness and citation guardrail results."""

from typing import Any

from app.schemas import CitationGuardrailResult, GuardrailClaim, TruthfulnessGuardrailResult
from app.services.guardrails.detectors import (
    find_claim_not_in_resume,
    find_exaggeration,
    find_sensitive_information,
    find_vague_answer,
    missing_citation_claim,
    resume_evidence_ids,
)
from app.services.guardrails.text import split_sentences

# Each flagged claim knocks this much off a perfect truthfulness score of 1.0.
_PENALTY_PER_CLAIM = 0.15


def evaluate_truthfulness(
    answer: str,
    evidence: list[dict[str, Any]],
    missing_citation_sentences: list[str],
    resume_text: str | None = None,
) -> TruthfulnessGuardrailResult:
    resume_ids = resume_evidence_ids(evidence)
    resume_text_lower = resume_text.lower() if resume_text else ""

    claims: list[GuardrailClaim] = [
        missing_citation_claim(sentence) for sentence in missing_citation_sentences
    ]

    for sentence in split_sentences(answer):
        for finding in (
            find_sensitive_information(sentence),
            find_exaggeration(sentence),
            find_claim_not_in_resume(sentence, resume_ids, resume_text_lower),
        ):
            if finding:
                claims.append(finding)

    vague_claim = find_vague_answer(answer)
    if vague_claim:
        claims.append(vague_claim)

    passed = not claims
    return TruthfulnessGuardrailResult(
        passed=passed,
        score=round(max(0.0, 1.0 - len(claims) * _PENALTY_PER_CLAIM), 2),
        summary=(
            "The answer is grounded, cites evidence, and does not contain risky claims."
            if passed
            else "The answer contains one or more truthfulness or clarity issues that should be reviewed."
        ),
        claims=claims,
        unsupported_claims=claims,
    )


def evaluate_citations(
    evidence: list[dict[str, Any]],
    cited_ids: list[str],
    missing_citation_sentences: list[str],
) -> CitationGuardrailResult:
    available_ids = {item.get("id") for item in evidence if item.get("id")}
    valid_cited_ids = [cid for cid in cited_ids if cid in available_ids]
    invalid_ids = [cid for cid in cited_ids if cid and cid not in available_ids]

    notes: list[str] = []
    if invalid_ids:
        notes.append("Some citations refer to evidence IDs that were not found in the retrieved context.")
    if not valid_cited_ids:
        notes.append("No supported evidence IDs were cited in the answer.")
    if missing_citation_sentences:
        notes.append("Some claims appear unsupported because they lack explicit evidence citations.")

    passed = not missing_citation_sentences and bool(valid_cited_ids)
    return CitationGuardrailResult(
        passed=passed,
        summary=(
            "Citations are present and match retrieved evidence."
            if passed
            else "Citation coverage is incomplete or unsupported evidence IDs were cited."
        ),
        cited_evidence_ids=valid_cited_ids,
        missing_citation_claims=missing_citation_sentences,
        weak_citation_notes=notes,
    )
