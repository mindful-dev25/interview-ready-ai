from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel

from app.config import settings


SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


class SessionStoreError(RuntimeError):
    """Raised when session state cannot be persisted or loaded."""


class SessionStore:
    """Local JSON session state store."""

    def __init__(self, path: str = settings.session_store_path) -> None:
        self.path = Path(path)

    async def save(self, session_id: str, state: Any) -> None:
        session_path = self._session_path(session_id)
        payload = self._normalize_state(session_id, state)
        self._write_json(session_path, payload)

    async def load(self, session_id: str) -> dict[str, Any] | None:
        session_path = self._session_path(session_id)
        if not session_path.exists():
            return None

        try:
            data = json.loads(session_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SessionStoreError(
                f"Session {session_id} is not valid JSON."
            ) from exc
        except OSError as exc:
            raise SessionStoreError(f"Failed to load session {session_id}.") from exc

        if not isinstance(data, dict):
            raise SessionStoreError(f"Session {session_id} did not contain an object.")
        return data

    async def update(self, session_id: str, patch: Any) -> dict[str, Any]:
        current = await self.load(session_id)
        now = self._timestamp()
        if current is None:
            current = {
                "session_id": session_id,
                "created_at": now,
            }

        patch_payload = self._to_json_safe(patch)
        if not isinstance(patch_payload, dict):
            raise TypeError("Session patch must be a mapping or Pydantic model.")

        merged = self._deep_merge(current, patch_payload)
        merged["session_id"] = session_id
        merged["updated_at"] = now
        self._write_json(self._session_path(session_id), merged)
        return merged

    def _normalize_state(self, session_id: str, state: Any) -> dict[str, Any]:
        payload = self._to_json_safe(state)
        if not isinstance(payload, dict):
            raise TypeError("Session state must be a mapping or Pydantic model.")

        state_session_id = payload.get("session_id")
        if state_session_id is not None and str(state_session_id) != session_id:
            raise ValueError(
                f"Session state id {state_session_id!r} does not match {session_id!r}."
            )

        now = self._timestamp()
        payload["session_id"] = session_id
        payload.setdefault("created_at", now)
        payload["updated_at"] = now
        return payload

    def _session_path(self, session_id: str) -> Path:
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            raise ValueError(
                "Session id may only contain letters, numbers, underscores, dots, and hyphens."
            )
        return self.path / f"{session_id}.json"

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(f"{path.suffix}.tmp")
            tmp_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(tmp_path, path)
        except OSError as exc:
            raise SessionStoreError(
                f"Failed to save session {payload['session_id']}."
            ) from exc

    def _deep_merge(
        self, current: dict[str, Any], patch: Mapping[str, Any]
    ) -> dict[str, Any]:
        merged = dict(current)
        for key, value in patch.items():
            if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _to_json_safe(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, Mapping):
            return {str(key): self._to_json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._to_json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._to_json_safe(item) for item in value]
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
