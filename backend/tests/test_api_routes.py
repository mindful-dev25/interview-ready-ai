"""End-to-end API tests. Every external call (web fetch, LLM) is replaced by a fake (see conftest.py)."""

import asyncio

from fastapi.testclient import TestClient
from fakes import EXPECTED_ANSWER_COUNT, JOB_PAGE_TEXT, RESUME_TEXT

from app.api.dependencies import get_llm_client
from app.core.llm import LLMClient
from app.main import app
from app.services.job_scraper import JobFetchError


def start_analysis(client: TestClient) -> dict:
    response = client.post(
        "/api/analysis", json={"job_url": "example.com/job", "resume_text": RESUME_TEXT}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_analysis_uses_a_pasted_job_description_instead_of_fetching(client, scraper):
    response = client.post(
        "/api/analysis",
        json={"job_url": "example.com/job", "job_text": "  We are hiring a Software Engineer.  ", "resume_text": RESUME_TEXT},
    )

    assert response.status_code == 200, response.text
    assert scraper.parsed_texts == ["We are hiring a Software Engineer."]
    assert scraper.fetched_urls == []
    assert response.json()["metadata"]["job_url"] == "https://example.com/job"


def test_analysis_accepts_a_pasted_job_description_without_a_url(client, scraper):
    response = client.post("/api/analysis", json={"job_text": "We are hiring a Software Engineer."})

    assert response.status_code == 200, response.text
    assert scraper.fetched_urls == []
    assert len(response.json()["answers"]) == EXPECTED_ANSWER_COUNT


def test_analysis_requires_a_job_url_or_a_pasted_description(client, scraper):
    response = client.post("/api/analysis", json={"job_url": "  ", "job_text": "  ", "resume_text": RESUME_TEXT})

    assert response.status_code == 422
    assert response.json()["detail"] == "A job URL or a pasted job description is required."
    assert scraper.fetched_urls == [] and scraper.parsed_texts == []


def test_analysis_stops_before_any_llm_work_when_the_job_page_cannot_be_read(client, scraper):
    scraper.fetch_error = JobFetchError("The job site refused automated access (HTTP 406). Paste it instead.")
    llm = app.dependency_overrides[get_llm_client]()

    response = client.post("/api/analysis", json={"job_url": "example.com/job", "resume_text": RESUME_TEXT})

    assert response.status_code == 422
    assert response.json()["detail"] == "The job site refused automated access (HTTP 406). Paste it instead."
    assert scraper.fetched_urls == ["https://example.com/job"]
    assert scraper.parsed_texts == []
    assert llm.prompts == []


def test_analysis_is_refused_when_the_llm_has_no_api_key(client, monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_llm_client, lambda: LLMClient(api_key="", model="test-model"))

    response = client.post("/api/analysis", json={"job_url": "example.com/job", "resume_text": RESUME_TEXT})

    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def review(client: TestClient, session_id: str, answer_id: str, action: str = "approve") -> dict:
    response = client.post(
        "/api/review", json={"session_id": session_id, "answer_id": answer_id, "action": action}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_analysis_drafts_an_answer_for_every_question(client):
    data = start_analysis(client)

    assert data["status"] == "needs_review"
    assert [answer["id"] for answer in data["answers"]] == [
        f"a{i}" for i in range(1, EXPECTED_ANSWER_COUNT + 1)
    ]
    assert all(answer["draft_answer"] for answer in data["answers"])
    assert all(answer["truthfulness_guardrail"]["summary"] for answer in data["answers"])
    assert data["metadata"]["job_url"] == "https://example.com/job"
    assert data["metadata"]["warnings"] == []


def test_analysis_reads_the_job_page_when_no_description_is_pasted(client, scraper):
    start_analysis(client)

    assert scraper.fetched_urls == ["https://example.com/job"]
    assert scraper.parsed_texts == [JOB_PAGE_TEXT]


def test_analysis_reports_a_job_parsing_fallback_as_a_warning(client, scraper):
    scraper.warning = "The job posting could not be analyzed in detail, so questions may be generic."

    data = start_analysis(client)

    assert data["metadata"]["warnings"] == [scraper.warning]


def test_review_returns_the_session_status(client):
    data = start_analysis(client)
    answer_ids = [answer["id"] for answer in data["answers"]]

    first = review(client, data["session_id"], answer_ids[0])
    assert first["human_status"] == "approved"
    assert first["answer"]["final_answer"] == first["answer"]["draft_answer"]
    assert first["session_status"] == "needs_review"

    # Asking for a revision must not mark the session complete.
    flagged = review(client, data["session_id"], answer_ids[1], action="request_revision")
    assert flagged["session_status"] == "needs_review"

    for answer_id in answer_ids[1:]:
        last = review(client, data["session_id"], answer_id)
    assert last["session_status"] == "complete"

    stored = client.get(f"/api/analysis/{data['session_id']}").json()
    assert stored["status"] == "complete"
    assert {answer["human_status"] for answer in stored["answers"]} == {"approved"}


def test_revision_keeps_reviews_made_while_the_llm_was_running(client, reviser):
    data = start_analysis(client)
    reviser.session_id = data["session_id"]

    response = client.post(
        "/api/revision",
        json={"session_id": data["session_id"], "answer_id": "a2", "reviewer_notes": "Be more specific."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["answer"]["draft_answer"] == "A revised answer."

    stored = client.get(f"/api/analysis/{data['session_id']}").json()
    statuses = {answer["id"]: answer["human_status"] for answer in stored["answers"]}
    assert statuses["a1"] == "approved"
    assert statuses["a2"] == "pending"
    assert stored["answers"][1]["draft_answer"] == "A revised answer."
    assert stored["answers"][1]["reviewer_notes"] == ["Be more specific."]


def test_revision_requires_notes(client):
    data = start_analysis(client)

    response = client.post(
        "/api/revision",
        json={"session_id": data["session_id"], "answer_id": "a1", "reviewer_notes": "  "},
    )

    assert response.status_code == 400


def test_report_is_available_only_after_every_answer_is_reviewed(client):
    data = start_analysis(client)
    session_id = data["session_id"]

    assert client.get(f"/api/report/{session_id}").status_code == 409

    for answer in data["answers"]:
        review(client, session_id, answer["id"])

    report = client.get(f"/api/report/{session_id}")
    assert report.status_code == 200, report.text
    markdown = report.json()["report_markdown"]
    assert markdown.startswith("# Final report\n\n## Interview Questions & Answers")
    # Every question is in the report with its full answer.
    for number, answer in enumerate(data["answers"], start=1):
        assert f"### Question {number}\n\n**{answer['question']['question']}**" in markdown
    assert len(report.json()["approved_answers"]) == EXPECTED_ANSWER_COUNT

    # The stored report is returned on later requests.
    assert client.get(f"/api/report/{session_id}").json()["report_markdown"] == markdown


def test_unknown_session_returns_404(client):
    assert client.get("/api/analysis/does-not-exist").status_code == 404
    assert client.get("/api/report/does-not-exist").status_code == 404


def test_a_stored_report_saved_with_a_table_is_served_as_lists(client, reviser):
    data = start_analysis(client)
    session_id = data["session_id"]
    for answer in data["answers"]:
        review(client, session_id, answer["id"])
    client.get(f"/api/report/{session_id}")

    # A report saved before tables were converted, as older sessions have.
    stored = asyncio.run(reviser.store.load(session_id))
    stored["final_report"]["report_markdown"] = "| Role | Evidence |\n|---|---|\n| Engineer | • A<br>• B |"
    asyncio.run(reviser.store.save(session_id, stored))

    report = client.get(f"/api/report/{session_id}").json()["report_markdown"]
    assert report == "**Engineer**\n\n- A\n- B"


def test_report_is_rebuilt_after_an_answer_is_revised_and_approved_again(client, reviser):
    data = start_analysis(client)
    session_id = data["session_id"]
    reviser.session_id = session_id
    for answer in data["answers"]:
        review(client, session_id, answer["id"])
    assert client.get(f"/api/report/{session_id}").status_code == 200

    revised = client.post(
        "/api/revision",
        json={"session_id": session_id, "answer_id": "a2", "reviewer_notes": "Be more specific."},
    )
    assert revised.status_code == 200, revised.text
    # Until the revised answer is reviewed, there is no report to show.
    assert client.get(f"/api/report/{session_id}").status_code == 409

    review(client, session_id, "a2")
    report = client.get(f"/api/report/{session_id}").json()

    approved = {answer["id"]: answer["final_answer"] for answer in report["approved_answers"]}
    assert approved["a2"] == "A revised answer."
