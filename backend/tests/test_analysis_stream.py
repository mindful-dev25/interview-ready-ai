"""Tests for the analysis endpoint that reports progress while it runs."""

import json

from fakes import EXPECTED_ANSWER_COUNT, RESUME_TEXT

from app.api.dependencies import get_llm_client
from app.core.llm import LLMClient
from app.main import app
from app.services.analysis_progress import ProgressReporter
from app.services.job_scraper import JobFetchError

JOB_TEXT = "We are hiring a Software Engineer to build and maintain APIs."


def stream_events(client, payload: dict) -> list[dict]:
    response = client.post("/api/analysis/stream", json=payload)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/x-ndjson")
    return [json.loads(line) for line in response.text.splitlines() if line]


def test_stream_reports_rising_progress_and_ends_with_the_result(client):
    events = stream_events(client, {"job_text": JOB_TEXT, "resume_text": RESUME_TEXT})

    *progress, result = events
    assert result["type"] == "result"
    assert len(result["data"]["answers"]) == EXPECTED_ANSWER_COUNT
    assert result["data"]["status"] == "needs_review"

    assert all(event["type"] == "progress" for event in progress)
    percents = [event["percent"] for event in progress]
    assert percents[0] == 0
    assert percents == sorted(percents)
    assert percents[-1] == 99
    assert progress[0]["message"] == "Reading the resume and the job posting"
    assert progress[-1]["message"] == f"Drafting answers ({EXPECTED_ANSWER_COUNT} of {EXPECTED_ANSWER_COUNT} done)"
    assert [event["phase"] for event in progress][-1] == "draft"


def test_stream_result_is_saved_and_can_be_reviewed(client):
    result = stream_events(client, {"job_text": JOB_TEXT, "resume_text": RESUME_TEXT})[-1]["data"]

    response = client.post(
        "/api/review", json={"session_id": result["session_id"], "answer_id": "a1", "action": "approve"}
    )

    assert response.status_code == 200, response.text


def test_stream_ends_with_an_error_event_when_no_job_is_given(client):
    events = stream_events(client, {"job_url": " ", "resume_text": RESUME_TEXT})

    assert events == [{"type": "error", "detail": "A job URL or a pasted job description is required."}]


def test_stream_ends_with_an_error_event_when_the_job_page_cannot_be_read(client, scraper):
    scraper.fetch_error = JobFetchError("The job site refused automated access (HTTP 406). Paste it instead.")

    events = stream_events(client, {"job_url": "example.com/job", "resume_text": RESUME_TEXT})

    assert events == [
        {"type": "progress", "phase": "resume", "percent": 0, "message": "Reading the resume and the job posting"},
        {"type": "error", "detail": "The job site refused automated access (HTTP 406). Paste it instead."},
    ]
    assert scraper.parsed_texts == []


def test_stream_is_refused_before_it_starts_when_the_llm_has_no_api_key(client, monkeypatch):
    monkeypatch.setitem(app.dependency_overrides, get_llm_client, lambda: LLMClient(api_key="", model="test-model"))

    response = client.post("/api/analysis/stream", json={"job_text": JOB_TEXT})

    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_progress_names_the_earliest_unfinished_step():
    updates = []
    reporter = ProgressReporter(updates.append)

    reporter.start()
    reporter.finish("job")
    reporter.finish("research")
    reporter.finish("resume")
    reporter.finish("questions")
    reporter.expect_drafts(4)
    reporter.draft_finished()

    assert [(update.phase, update.percent, update.message) for update in updates] == [
        ("resume", 0, "Reading the resume and the job posting"),
        ("resume", 15, "Reading the resume"),
        ("resume", 25, "Reading the resume"),
        ("draft", 35, "Writing interview questions"),
        ("draft", 55, "Drafting answers"),
        ("draft", 55, "Drafting answers (0 of 4 done)"),
        ("draft", 66, "Drafting answers (1 of 4 done)"),
    ]
