"""Individual heuristics that flag risky sentences or answers."""

from typing import Any

from app.schemas import GuardrailClaim
from app.services.guardrails.text import (
    EXAGGERATION_TERMS,
    EXAMPLE_TRIGGERS,
    SENSITIVE_PATTERNS,
    extract_evidence_ids,
    has_assertion,
    has_citation,
    has_personal_reference,
    long_words,
    split_sentences,
)

# Answers shorter than this are too brief to judge as vague.
_MIN_VAGUE_ANSWER_LENGTH = 80
# When an answer cites nothing at all, flag long assertive sentences even without "I/we".
_MIN_UNCITED_ASSERTION_LENGTH = 40


def find_missing_citation_claims(answer: str, cited_ids: list[str]) -> list[str]:
    """Sentences that assert past work but carry no citation."""
    cited_in_answer = bool(cited_ids)
    missing: list[str] = []

    for sentence in split_sentences(answer):
        if not has_assertion(sentence):
            continue
        if has_personal_reference(sentence) and not has_citation(sentence):
            missing.append(sentence)
        elif not cited_in_answer and len(sentence) > _MIN_UNCITED_ASSERTION_LENGTH:
            missing.append(sentence)

    return missing


def find_sensitive_information(sentence: str) -> GuardrailClaim | None:
    if not any(pattern.search(sentence) for pattern in SENSITIVE_PATTERNS):
        return None
    return GuardrailClaim(
        claim=sentence,
        supported=False,
        evidence_ids=[],
        explanation="The answer contains private or sensitive information that should not be shared.",
        severity="high",
        suggested_fix="Remove personal identifiers and sensitive details from the response.",
    )


def find_exaggeration(sentence: str) -> GuardrailClaim | None:
    lower = sentence.lower()
    if not any(term in lower for term in EXAGGERATION_TERMS):
        return None

    cited = has_citation(sentence)
    explanation = (
        "This sentence may overstate seniority or responsibility."
        if cited
        else "This sentence may exaggerate responsibilities without clear evidence."
    )
    return GuardrailClaim(
        claim=sentence,
        supported=cited,
        evidence_ids=extract_evidence_ids(sentence) if cited else [],
        explanation=explanation,
        severity="medium",
        suggested_fix="Use more measured language and align it with documented evidence.",
    )


def find_claim_not_in_resume(
    sentence: str,
    resume_evidence_ids: set[str],
    resume_text_lower: str,
) -> GuardrailClaim | None:
    """Flag a personal assertion that neither cites resume evidence nor overlaps the resume text."""
    if not has_personal_reference(sentence) or not has_assertion(sentence):
        return None
    if set(extract_evidence_ids(sentence)) & resume_evidence_ids:
        return None
    if resume_text_lower and any(word in resume_text_lower for word in long_words(sentence)):
        return None

    return GuardrailClaim(
        claim=sentence,
        supported=False,
        evidence_ids=[],
        explanation="This personal claim is not supported by the resume evidence.",
        severity="high",
        suggested_fix="Keep the answer grounded in documented resume achievements.",
    )


def find_vague_answer(answer: str) -> GuardrailClaim | None:
    if len(answer) < _MIN_VAGUE_ANSWER_LENGTH:
        return None
    lower = answer.lower()
    if any(trigger in lower for trigger in EXAMPLE_TRIGGERS):
        return None

    return GuardrailClaim(
        claim=answer,
        supported=False,
        evidence_ids=[],
        explanation="The answer is generic and lacks concrete examples or measurable results.",
        severity="medium",
        suggested_fix="Add a specific example with evidence-backed results to make the answer more persuasive.",
    )


def missing_citation_claim(sentence: str) -> GuardrailClaim:
    return GuardrailClaim(
        claim=sentence,
        supported=False,
        evidence_ids=[],
        explanation="This claim appears to be factual or personal but lacks a source citation.",
        severity="high",
        suggested_fix="Cite relevant evidence or make the statement clearly subjective.",
    )


def resume_evidence_ids(evidence: list[dict[str, Any]]) -> set[str]:
    return {
        item["id"]
        for item in evidence
        if item.get("source_type") == "resume" and item.get("id")
    }
