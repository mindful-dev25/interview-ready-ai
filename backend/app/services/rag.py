class RAGService:
    """Placeholder retrieval service over resume, job, and company context."""

    async def index_context(self, session_id: str, documents: list[str]) -> None:
        # TODO: Chunk, embed, and persist documents in Chroma.
        _ = (session_id, documents)

    async def retrieve(self, session_id: str, query: str) -> list[dict[str, str]]:
        # TODO: Retrieve relevant evidence for answer drafting.
        _ = (session_id, query)
        return []
