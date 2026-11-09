"""Keyword-overlap scoring and ranking of stored records against a query."""

from collections import Counter
from typing import Any

from app.storage.vector_store.text import token_counts

_MAX_KEYWORDS_IN_RELEVANCE = 8


def rank_records(
    records: list[dict[str, Any]], query: str, limit: int
) -> list[dict[str, Any]]:
    query_tokens = token_counts(query)
    scored = [_score_record(record, query_tokens) for record in records]
    scored.sort(
        key=lambda result: (
            result["score"],
            len(result.get("matched_keywords", [])),
            result["id"],
        ),
        reverse=True,
    )
    return [_to_search_result(result) for result in scored[:limit]]


def _score_record(record: dict[str, Any], query_tokens: Counter[str]) -> dict[str, Any]:
    """Score = shared token occurrences + share of query covered + match density in the record."""
    record_tokens = Counter(record.get("token_counts", {}))
    matched_keywords = sorted(set(query_tokens) & set(record_tokens))

    if not query_tokens:
        score = 0.0
    else:
        weighted_matches = sum(
            min(query_tokens[token], record_tokens[token]) for token in matched_keywords
        )
        coverage = len(matched_keywords) / len(query_tokens)
        density = weighted_matches / max(sum(record_tokens.values()), 1)
        score = round(weighted_matches + coverage + density, 4)

    return {**record, "score": score, "matched_keywords": matched_keywords}


def _to_search_result(record: dict[str, Any]) -> dict[str, Any]:
    matched_keywords = record.get("matched_keywords", [])
    relevance = (
        "Matched keywords: " + ", ".join(matched_keywords[:_MAX_KEYWORDS_IN_RELEVANCE])
        if matched_keywords
        else "No strong keyword match; included as available context."
    )

    return {
        "id": record["id"],
        "source_type": record["source_type"],
        "source": record["source"],
        "quote": record["quote"],
        "relevance": relevance,
        "source_url": record.get("source_url"),
        "score": record["score"],
        "metadata": record.get("metadata", {}),
    }
