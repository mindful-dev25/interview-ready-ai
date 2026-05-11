from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.storage.vector_store import DocumentInput, VectorStore


DEFAULT_CONTEXT_SOURCES = (
    ("resume", "Resume"),
    ("job_description", "Job description"),
    ("company_research", "Company research"),
)


class RAGService:
    """Retrieval service over resume, job, and company context."""

    def __init__(self, vector_store: VectorStore | None = None) -> None:
        self.vector_store = vector_store or VectorStore()

    async def index_context(
        self, session_id: str, documents: list[DocumentInput]
    ) -> None:
        normalized_documents = [
            self._normalize_context_document(document, index)
            for index, document in enumerate(documents)
        ]
        await self.vector_store.replace_documents(
            self._collection_name(session_id),
            normalized_documents,
        )

    async def retrieve(
        self, session_id: str, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        return await self.vector_store.similarity_search(
            self._collection_name(session_id),
            query,
            limit=limit,
        )

    def format_evidence_for_prompt(self, evidence: list[dict[str, Any]]) -> str:
        """Render retrieved evidence with stable citation IDs for answer prompts."""
        lines: list[str] = []
        for item in evidence:
            evidence_id = item.get("id", "evidence")
            source_type = item.get("source_type", "context")
            source = item.get("source", "Context")
            quote = item.get("quote", "").strip()
            if quote:
                lines.append(f"[{evidence_id}] {source_type} - {source}: {quote}")
        return "\n".join(lines)

    def _normalize_context_document(
        self, document: DocumentInput, index: int
    ) -> dict[str, Any]:
        if isinstance(document, Mapping):
            return dict(document)

        source_type, source = self._default_source(index)
        return {
            "content": document,
            "source_type": source_type,
            "source": source,
            "metadata": {"context_index": index},
        }

    def _default_source(self, index: int) -> tuple[str, str]:
        if index < len(DEFAULT_CONTEXT_SOURCES):
            return DEFAULT_CONTEXT_SOURCES[index]
        return ("generated", f"Context document {index + 1}")

    def _collection_name(self, session_id: str) -> str:
        return f"session-{session_id}-context"
