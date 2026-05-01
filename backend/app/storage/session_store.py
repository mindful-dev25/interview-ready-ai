from app.config import settings


class SessionStore:
    """Placeholder session state store."""

    def __init__(self, path: str = settings.session_store_path) -> None:
        self.path = path

    async def save(self, session_id: str, state: dict) -> None:
        # TODO: Persist workflow state locally.
        _ = (session_id, state)

    async def load(self, session_id: str) -> dict | None:
        # TODO: Load workflow state by session id.
        _ = session_id
        return None
