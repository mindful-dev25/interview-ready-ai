from fastapi.testclient import TestClient
from pydantic import HttpUrl

from app.main import app
from app.api import routes
from app.storage.session_store import SessionStore


def test_analysis_and_review_route_smoke(tmp_path):
    routes.session_store = SessionStore(path=str(tmp_path))
    client = TestClient(app)

    response = client.post(
        "/api/analysis",
        json={
            "job_url": "http://example.com/job",
            "resume_text": "Summary: Experienced engineer. Experience: Owned product delivery and technical leadership. Skills: Python, APIs, cloud. Education: B.S. Computer Science. "
            "Additional text to satisfy word count and resume structure requirements.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert isinstance(data.get("answers"), list)
    assert len(data["answers"]) == 2

    session_id = data["session_id"]
    answer_id = data["answers"][0]["id"]

    review_response = client.post(
        "/api/review",
        json={
            "session_id": session_id,
            "answer_id": answer_id,
            "action": "approve",
        },
    )
    assert review_response.status_code == 200
    review_data = review_response.json()
    assert review_data["human_status"] == "approved"
    assert review_data["answer"]["final_answer"] == review_data["answer"]["draft_answer"]

    state_response = client.get(f"/api/analysis/{session_id}")
    assert state_response.status_code == 200
    state_data = state_response.json()
    assert state_data["answers"][0]["human_status"] == "approved"
