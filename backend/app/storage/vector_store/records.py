"""Turn caller-supplied documents into stored, chunked evidence records."""

from collections.abc import Mapping
import hashlib
from typing import Any

from app.storage.vector_store.text import chunk_text, clean_text, token_counts

DocumentInput = str | Mapping[str, Any]


def build_records(collection: str, documents: list[DocumentInput]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for document_index, document in enumerate(documents):
        normalized = normalize_document(document, document_index)
        for chunk_index, chunk in enumerate(chunk_text(normalized["content"])):
            records.append(_build_record(collection, normalized, chunk, chunk_index))
    return records


def normalize_document(document: DocumentInput, document_index: int) -> dict[str, Any]:
    if isinstance(document, str):
        return {
            "content": clean_text(document),
            "source_type": "generated",
            "source": f"Document {document_index + 1}",
            "source_url": None,
            "metadata": {"document_index": document_index},
        }

    content = str(
        document.get("content")
        or document.get("text")
        or document.get("quote")
        or ""
    )
    source_type = str(document.get("source_type") or "generated")
    raw_source_url = document.get("source_url")
    raw_metadata = document.get("metadata")
    metadata = _json_safe_dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
    metadata["document_index"] = document_index

    return {
        "content": clean_text(content),
        "source_type": source_type,
        "source": str(document.get("source") or source_type.replace("_", " ").title()),
        "source_url": str(raw_source_url) if raw_source_url else None,
        "metadata": metadata,
    }


def _build_record(
    collection: str,
    document: dict[str, Any],
    chunk: str,
    chunk_index: int,
) -> dict[str, Any]:
    # Deterministic ID so re-indexing the same chunk overwrites instead of duplicating.
    fingerprint = hashlib.sha256(
        "|".join(
            [collection, document["source_type"], document["source"], str(chunk_index), chunk]
        ).encode("utf-8")
    ).hexdigest()[:16]

    return {
        "id": f"evidence-{fingerprint}",
        "source_type": document["source_type"],
        "source": document["source"],
        "source_url": document["source_url"],
        "quote": chunk,
        "token_counts": dict(token_counts(chunk)),
        "metadata": {**document["metadata"], "chunk_index": chunk_index},
    }


def _json_safe_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): item if isinstance(item, (str, int, float, bool)) or item is None else str(item)
        for key, item in value.items()
    }
