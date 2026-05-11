from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from app.config import settings


DocumentInput = str | Mapping[str, Any]

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9+#.'-]*")
COLLECTION_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")
MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 120
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
    "you",
    "your",
}


class VectorStore:
    """Keyword-backed retrieval store with a Chroma-compatible boundary.

    This MVP intentionally avoids embedding model dependencies. Records are
    persisted as JSON under the configured Chroma directory so a Chroma-backed
    implementation can replace the internals without changing service callers.
    """

    def __init__(self, persist_dir: str = settings.chroma_persist_dir) -> None:
        self.persist_dir = Path(persist_dir)
        self.index_dir = self.persist_dir / "keyword_index"

    async def add_documents(
        self, collection: str, documents: list[DocumentInput]
    ) -> None:
        records = self._load_collection(collection)
        records_by_id = {
            record["id"]: record
            for record in records
            if isinstance(record.get("id"), str)
        }

        for document_index, document in enumerate(documents):
            normalized = self._normalize_document(document, document_index)
            for chunk_index, chunk in enumerate(self._chunk_text(normalized["content"])):
                record = self._build_record(
                    collection=collection,
                    document=normalized,
                    chunk=chunk,
                    chunk_index=chunk_index,
                )
                records_by_id[record["id"]] = record

        self._write_collection(collection, list(records_by_id.values()))

    async def replace_documents(
        self, collection: str, documents: list[DocumentInput]
    ) -> None:
        records: list[dict[str, Any]] = []

        for document_index, document in enumerate(documents):
            normalized = self._normalize_document(document, document_index)
            for chunk_index, chunk in enumerate(self._chunk_text(normalized["content"])):
                records.append(
                    self._build_record(
                        collection=collection,
                        document=normalized,
                        chunk=chunk,
                        chunk_index=chunk_index,
                    )
                )

        self._write_collection(collection, records)

    async def similarity_search(
        self, collection: str, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        records = self._load_collection(collection)
        if not records or limit <= 0:
            return []

        query_tokens = self._token_counts(query)
        scored = [
            self._score_record(record, query_tokens)
            for record in records
        ]
        scored.sort(
            key=lambda result: (
                result["score"],
                len(result.get("matched_keywords", [])),
                result["id"],
            ),
            reverse=True,
        )

        return [self._to_search_result(result) for result in scored[:limit]]

    def _normalize_document(
        self, document: DocumentInput, document_index: int
    ) -> dict[str, Any]:
        if isinstance(document, str):
            content = document
            source_type = "generated"
            source = f"Document {document_index + 1}"
            source_url = None
            metadata: dict[str, Any] = {"document_index": document_index}
        else:
            content = str(
                document.get("content")
                or document.get("text")
                or document.get("quote")
                or ""
            )
            source_type = str(document.get("source_type") or "generated")
            source = str(document.get("source") or source_type.replace("_", " ").title())
            raw_source_url = document.get("source_url")
            source_url = str(raw_source_url) if raw_source_url else None
            raw_metadata = document.get("metadata")
            metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
            metadata = self._json_safe_dict(metadata)
            metadata["document_index"] = document_index

        content = self._clean_text(content)
        if not content:
            return {
                "content": "",
                "source_type": source_type,
                "source": source,
                "source_url": source_url,
                "metadata": metadata,
            }

        return {
            "content": content,
            "source_type": source_type,
            "source": source,
            "source_url": source_url,
            "metadata": metadata,
        }

    def _build_record(
        self,
        collection: str,
        document: dict[str, Any],
        chunk: str,
        chunk_index: int,
    ) -> dict[str, Any]:
        fingerprint = hashlib.sha256(
            "|".join(
                [
                    collection,
                    document["source_type"],
                    document["source"],
                    str(chunk_index),
                    chunk,
                ]
            ).encode("utf-8")
        ).hexdigest()[:16]
        token_counts = self._token_counts(chunk)

        metadata = dict(document["metadata"])
        metadata["chunk_index"] = chunk_index

        return {
            "id": f"evidence-{fingerprint}",
            "source_type": document["source_type"],
            "source": document["source"],
            "source_url": document["source_url"],
            "quote": chunk,
            "token_counts": dict(token_counts),
            "metadata": metadata,
        }

    def _score_record(
        self, record: dict[str, Any], query_tokens: Counter[str]
    ) -> dict[str, Any]:
        record_tokens = Counter(record.get("token_counts", {}))
        matched_keywords = sorted(set(query_tokens) & set(record_tokens))
        if not query_tokens:
            score = 0.0
        else:
            weighted_matches = sum(
                min(query_tokens[token], record_tokens[token])
                for token in matched_keywords
            )
            coverage = len(matched_keywords) / len(query_tokens)
            density = weighted_matches / max(sum(record_tokens.values()), 1)
            score = round(weighted_matches + coverage + density, 4)

        result = dict(record)
        result["score"] = score
        result["matched_keywords"] = matched_keywords
        return result

    def _to_search_result(self, record: dict[str, Any]) -> dict[str, Any]:
        matched_keywords = record.get("matched_keywords", [])
        relevance = (
            "Matched keywords: " + ", ".join(matched_keywords[:8])
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

    def _chunk_text(self, text: str) -> list[str]:
        text = self._clean_text(text)
        if not text:
            return []

        paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
        chunks: list[str] = []
        current = ""

        for paragraph in paragraphs:
            pending = self._split_long_text(paragraph)
            for part in pending:
                if not current:
                    current = part
                    continue
                if len(current) + len(part) + 2 <= MAX_CHUNK_CHARS:
                    current = f"{current}\n\n{part}"
                    continue

                chunks.append(current)
                overlap = current[-CHUNK_OVERLAP_CHARS:].strip()
                current = f"{overlap}\n\n{part}" if overlap else part

        if current:
            chunks.append(current)

        return chunks

    def _split_long_text(self, text: str) -> list[str]:
        if len(text) <= MAX_CHUNK_CHARS:
            return [text]

        parts: list[str] = []
        remaining = text
        while len(remaining) > MAX_CHUNK_CHARS:
            split_at = remaining.rfind(" ", 0, MAX_CHUNK_CHARS)
            if split_at < MAX_CHUNK_CHARS // 2:
                split_at = MAX_CHUNK_CHARS
            parts.append(remaining[:split_at].strip())
            overlap_start = max(split_at - CHUNK_OVERLAP_CHARS, 0)
            remaining = remaining[overlap_start:].strip()

        if remaining:
            parts.append(remaining)
        return parts

    def _load_collection(self, collection: str) -> list[dict[str, Any]]:
        path = self._collection_path(collection)
        if not path.exists():
            return []

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(data, list):
            return []
        return [record for record in data if isinstance(record, dict)]

    def _write_collection(self, collection: str, records: list[dict[str, Any]]) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._collection_path(collection).write_text(
            json.dumps(records, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _collection_path(self, collection: str) -> Path:
        safe_name = COLLECTION_PATTERN.sub("-", collection).strip("-") or "default"
        return self.index_dir / f"{safe_name}.json"

    def _token_counts(self, text: str) -> Counter[str]:
        tokens = [
            token
            for token in TOKEN_PATTERN.findall(text.lower())
            if len(token) > 1 and token not in STOP_WORDS
        ]
        return Counter(tokens)

    def _clean_text(self, text: str) -> str:
        normalized_lines = [
            re.sub(r"[ \t]+", " ", line).strip()
            for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        ]
        blocks: list[str] = []
        current: list[str] = []
        for line in normalized_lines:
            if line:
                current.append(line)
                continue
            if current:
                blocks.append(" ".join(current))
                current = []
        if current:
            blocks.append(" ".join(current))
        return "\n\n".join(blocks)

    def _json_safe_dict(self, value: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, (str, int, float, bool)) or item is None:
                safe[str(key)] = item
            else:
                safe[str(key)] = str(item)
        return safe
