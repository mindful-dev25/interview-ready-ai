from pathlib import Path
from typing import Any

from app.config import settings
from app.storage.vector_store.persistence import CollectionFiles
from app.storage.vector_store.records import DocumentInput, build_records
from app.storage.vector_store.scoring import rank_records


class VectorStore:
    """Keyword-backed retrieval store with a Chroma-compatible boundary.

    This MVP intentionally avoids embedding model dependencies. Records are
    persisted as JSON under the configured Chroma directory so a Chroma-backed
    implementation can replace the internals without changing service callers.
    """

    def __init__(self, persist_dir: str = settings.chroma_persist_dir) -> None:
        self.persist_dir = Path(persist_dir)
        self.index_dir = self.persist_dir / "keyword_index"
        self._files = CollectionFiles(self.index_dir)

    async def add_documents(self, collection: str, documents: list[DocumentInput]) -> None:
        """Merge documents into the collection, overwriting chunks with the same ID."""
        records_by_id = {
            record["id"]: record
            for record in self._files.load(collection)
            if isinstance(record.get("id"), str)
        }
        for record in build_records(collection, documents):
            records_by_id[record["id"]] = record
        self._files.write(collection, list(records_by_id.values()))

    async def replace_documents(self, collection: str, documents: list[DocumentInput]) -> None:
        self._files.write(collection, build_records(collection, documents))

    async def similarity_search(
        self, collection: str, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        records = self._files.load(collection)
        if not records or limit <= 0:
            return []
        return rank_records(records, query, limit)
