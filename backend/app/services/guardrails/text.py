"""Vocabularies, regexes and small text helpers shared by the guardrail checks."""

import re

SENSITIVE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{3}[ .-]?\d{2}[ .-]?\d{4}\b",  # SSN alternate
        r"\b\d{3}[ .-]?\d{3}[ .-]?\d{4}\b",  # phone number
        r"\b\w+@\w+\.\w+\b",  # email
        r"\b\$\d+[\d,]*\b",  # salary
        r"\b(salary|compensation|pay|bank account|credit card)\b",
        r"\b(confidential|proprietary|secret|private data)\b",
    )
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

# Phrases that signal the answer includes a concrete example.
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

# Verbs that turn a sentence into a factual claim about past work.
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

_CITATION_RE = re.compile(r"\[([^\]]+)\]")
_PERSONAL_REFERENCE_RE = re.compile(r"\b(i|my|we|our|me)\b")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")
_LONG_WORD_RE = re.compile(r"\b\w{4,}\b")


def split_sentences(text: str) -> list[str]:
    sentences = _SENTENCE_BOUNDARY_RE.split(text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def extract_evidence_ids(text: str) -> list[str]:
    """Return the unique ``[id]`` citations found in the text."""
    return list({match.group(1).strip() for match in _CITATION_RE.finditer(text)})


def strip_citations(text: str) -> str:
    return _CITATION_RE.sub("", text)


def has_citation(text: str) -> bool:
    return bool(_CITATION_RE.search(text))


def has_personal_reference(text: str) -> bool:
    return bool(_PERSONAL_REFERENCE_RE.search(text.lower()))


def has_assertion(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in ASSERTION_TERMS)


def long_words(text: str) -> list[str]:
    return _LONG_WORD_RE.findall(text.lower())
