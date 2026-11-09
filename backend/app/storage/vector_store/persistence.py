"""JSON-file persistence for vector store collections."""

import json
from pathlib import Path
import re
from typing import Any

_UNSAFE_COLLECTION_CHARS = re.compile(r"[^a-zA-Z0-9_.-]+")


class CollectionFiles:
    """Stores each collection as a JSON list of records in ``index_dir``."""

    def __init__(self, index_dir: Path) -> None:
        self.index_dir = index_dir

    def load(self, collection: str) -> list[dict[str, Any]]:
        """Return the collection's records; missing or unreadable files count as empty."""
        path = self._path(collection)
        if not path.exists():
            return []

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(data, list):
            return []
        return [record for record in data if isinstance(record, dict)]

    def write(self, collection: str, records: list[dict[str, Any]]) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._path(collection).write_text(
            json.dumps(records, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def _path(self, collection: str) -> Path:
        safe_name = _UNSAFE_COLLECTION_CHARS.sub("-", collection).strip("-") or "default"
        return self.index_dir / f"{safe_name}.json"
