from app.config import settings


class VectorStore:
    """Placeholder Chroma vector store adapter."""

    def __init__(self, persist_dir: str = settings.chroma_persist_dir) -> None:
        self.persist_dir = persist_dir

    async def add_documents(self, collection: str, documents: list[str]) -> None:
        # TODO: Persist embedded documents to Chroma.
        _ = (collection, documents)

    async def similarity_search(self, collection: str, query: str, limit: int = 5) -> list[dict[str, str]]:
        # TODO: Query Chroma for relevant chunks.
        _ = (collection, query, limit)
        return []
