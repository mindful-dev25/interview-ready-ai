import asyncio
from pathlib import Path

from app.storage.session_store import SessionStore


def test_session_store_save_and_load(tmp_path):
    store = SessionStore(path=str(tmp_path))
    session_id = "session-test"
    payload = {"session_id": session_id, "foo": "bar"}

    asyncio.run(store.save(session_id, payload))
    loaded = asyncio.run(store.load(session_id))

    assert loaded is not None
    assert loaded["session_id"] == session_id
    assert loaded["foo"] == "bar"
    assert Path(tmp_path / f"{session_id}.json").exists()
