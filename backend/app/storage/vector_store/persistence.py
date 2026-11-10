"""JSON-file persistence for vector store collections."""

from collections import OrderedDict
import json
from pathlib import Path
import re
from typing import Any

_UNSAFE_COLLECTION_CHARS = re.compile(r"[^a-zA-Z0-9_.-]+")
# Recently read collections kept in memory, so repeated searches skip the disk read and JSON parse.
_CACHE_SIZE = 16


class CollectionFiles:
    """Stores each collection as a JSON list of records in ``index_dir``."""

    def __init__(self, index_dir: Path) -> None:
        self.index_dir = index_dir
        # path -> (file modification time, records); stale entries are detected by the mtime.
        self._cache: OrderedDict[Path, tuple[int, list[dict[str, Any]]]] = OrderedDict()

    def load(self, collection: str) -> list[dict[str, Any]]:
        """Return the collection's records; missing or unreadable files count as empty.

        The returned list may be shared with the cache, so callers must not mutate it.
        """
        path = self._path(collection)
        try:
            modified = path.stat().st_mtime_ns
        except OSError:
            return []

        cached = self._cache.get(path)
        if cached is not None and cached[0] == modified:
            self._cache.move_to_end(path)
            return cached[1]

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        records = [record for record in data if isinstance(record, dict)] if isinstance(data, list) else []
        self._cache[path] = (modified, records)
        while len(self._cache) > _CACHE_SIZE:
            self._cache.popitem(last=False)
        return records

    def write(self, collection: str, records: list[dict[str, Any]]) -> None:
        path = self._path(collection)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, indent=2, sort_keys=True), encoding="utf-8")
        self._cache.pop(path, None)

    def _path(self, collection: str) -> Path:
        safe_name = _UNSAFE_COLLECTION_CHARS.sub("-", collection).strip("-") or "default"
        return self.index_dir / f"{safe_name}.json"
