"""Fixtures shared by the API tests: the real app wired to fake services, with nothing on the network."""

import pytest
from fastapi.testclient import TestClient
from fakes import (
    DRAFT_REPLY,
    FakeCompanyResearch,
    FakeLLM,
    FakeQuestionGenerator,
    FakeResumeParser,
    FakeScraper,
    ReviserThatApprovesAnotherAnswerMeanwhile,
)

from app.api.dependencies import (
    get_analysis_pipeline,
    get_answer_reviser,
    get_llm_client,
    get_report_generator,
    get_session_store,
)
from app.config import settings
from app.main import app
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.answer_drafter import AnswerDrafter
from app.services.guardrails import GuardrailService
from app.services.rag import RAGService
from app.services.report_generator import ReportGenerator
from app.storage.session_store import SessionStore
from app.storage.vector_store import VectorStore


@pytest.fixture
def scraper() -> FakeScraper:
    return FakeScraper()


@pytest.fixture
def reviser(tmp_path) -> ReviserThatApprovesAnotherAnswerMeanwhile:
    return ReviserThatApprovesAnotherAnswerMeanwhile(SessionStore(path=str(tmp_path / "sessions")))


@pytest.fixture
def client(tmp_path, monkeypatch, scraper, reviser) -> TestClient:
    # The API tests run signed out, even when backend/.env turns on Google sign-in.
    monkeypatch.setattr(settings, "google_client_id", "")
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
        get_llm_client: lambda: llm,
        get_answer_reviser: lambda: reviser,
        get_report_generator: lambda: report_generator,
    }
    for dependency, provider in overrides.items():
        monkeypatch.setitem(app.dependency_overrides, dependency, provider)
    return TestClient(app)
