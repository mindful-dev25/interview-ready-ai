"""End-to-end API tests. Every external call (web fetch, LLM) is replaced by a fake."""

import pytest
from fastapi.testclient import TestClient
from fakes import FakeLLM

from app.api.dependencies import (
    get_analysis_pipeline,
    get_answer_reviser,
    get_report_generator,
    get_session_store,
)
from app.main import app
from app.schemas import HumanReviewStatus, InterviewQuestion, SessionState
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.answer_drafter import AnswerDrafter
from app.services.guardrails import GuardrailService
from app.services.rag import RAGService
from app.services.report_generator import ReportGenerator
from app.storage.session_store import SessionStore
from app.storage.vector_store import VectorStore

DRAFT_REPLY = "- Draft Answer: I enjoy solving problems with clear, well tested code.\n- Evidence Used: none"
RESUME_TEXT = "Summary: engineer. Experience: built APIs. Skills: Python. Education: B.S. Computer Science."
GENERATED_QUESTION_COUNT = 3
# Two fixed openers, the generated questions, and one fixed closer.
EXPECTED_ANSWER_COUNT = GENERATED_QUESTION_COUNT + 3


class FakeScraper:
    def __init__(self) -> None:
        self.warning: str | None = None

    async def scrape(self, job_url: str) -> dict:
        return {
            "title": "Software Engineer",
            "company": "Example Corp",
            "location": "Remote",
            "responsibilities": ["Build and maintain APIs."],
            "required_skills": ["Python"],
            "preferred_skills": [],
            "keywords": [],
            "raw_text": "Example Corp is hiring a Software Engineer to build and maintain APIs.",
            "warning": self.warning,
        }


class FakeResumeParser:
    async def parse_text(self, resume_text: str) -> dict:
        return {"candidate_summary": "Engineer", "skills": ["Python"]}


class FakeCompanyResearch:
    async def research(self, company_name: str, job_page_text: str) -> dict:
        return {"company_name": company_name, "summary": "Builds developer tools.", "values": ["Ownership"]}


class FakeQuestionGenerator:
    async def generate_questions(self, **kwargs) -> list[InterviewQuestion]:
        return [
            InterviewQuestion(id=f"generated-{i}", question=f"Tailored question {i}?")
            for i in range(GENERATED_QUESTION_COUNT)
        ]


class ReviserThatApprovesAnotherAnswerMeanwhile:
    """Simulates a user approving answer a1 while the LLM is still revising another answer."""

    def __init__(self, store: SessionStore) -> None:
        self.store = store

    async def revise(self, answer, reviewer_notes: str) -> str:
        session_id = self.session_id
        session = SessionState.model_validate(await self.store.load(session_id))
        session.answers[0].human_status = HumanReviewStatus.approved
        await self.store.save(session_id, session)
        return "A revised answer."


@pytest.fixture
def scraper() -> FakeScraper:
    return FakeScraper()


@pytest.fixture
def reviser(tmp_path) -> ReviserThatApprovesAnotherAnswerMeanwhile:
    return ReviserThatApprovesAnotherAnswerMeanwhile(SessionStore(path=str(tmp_path / "sessions")))


@pytest.fixture
def client(tmp_path, monkeypatch, scraper, reviser) -> TestClient:
    rag = RAGService(VectorStore(persist_dir=str(tmp_path / "index")))
    llm = FakeLLM(DRAFT_REPLY)
    pipeline = AnalysisPipeline(
        job_scraper=scraper,
        resume_parser=FakeResumeParser(),
        company_research_service=FakeCompanyResearch(),
        rag_service=rag,
        question_generator=FakeQuestionGenerator(),
        answer_drafter=AnswerDrafter(
            rag_service=rag, llm_client=llm, guardrails=GuardrailService(llm_client=llm)
        ),
    )
    report_generator = ReportGenerator(llm_client=FakeLLM("# Final report"))

    overrides = {
        get_session_store: lambda: reviser.store,
        get_analysis_pipeline: lambda: pipeline,
        get_answer_reviser: lambda: reviser,
        get_report_generator: lambda: report_generator,
    }
    for dependency, provider in overrides.items():
        monkeypatch.setitem(app.dependency_overrides, dependency, provider)
    return TestClient(app)


def start_analysis(client: TestClient) -> dict:
    response = client.post(
        "/api/analysis", json={"job_url": "example.com/job", "resume_text": RESUME_TEXT}
    )
    assert response.status_code == 200, response.text
    return response.json()


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


def test_analysis_reports_scraper_fallback_as_a_warning(client, scraper):
    scraper.warning = "Failed to fetch job posting: HTTP 404."

    data = start_analysis(client)

    assert data["metadata"]["warnings"] == ["Failed to fetch job posting: HTTP 404."]


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
    assert report.json()["report_markdown"] == "# Final report"
    assert len(report.json()["approved_answers"]) == EXPECTED_ANSWER_COUNT

    # The stored report is returned on later requests.
    assert client.get(f"/api/report/{session_id}").json()["report_markdown"] == "# Final report"


def test_unknown_session_returns_404(client):
    assert client.get("/api/analysis/does-not-exist").status_code == 404
    assert client.get("/api/report/does-not-exist").status_code == 404
