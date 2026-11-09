"""Shared service instances for the API layer, injected via FastAPI ``Depends``.

Each getter is cached so the whole app shares one instance. Tests can swap any of
them with ``app.dependency_overrides[get_x] = lambda: fake``.
"""

from functools import lru_cache

from app.services.analysis_pipeline import AnalysisPipeline
from app.services.answer_drafter import AnswerDrafter
from app.services.answer_reviser import AnswerReviser
from app.services.company_research import CompanyResearchService
from app.services.job_scraper import JobScraper
from app.services.question_generator import QuestionGenerator
from app.services.rag import RAGService
from app.services.report_generator import ReportGenerator
from app.services.resume_parser import ResumeParser
from app.storage.session_store import SessionStore


@lru_cache
def get_session_store() -> SessionStore:
    return SessionStore()


@lru_cache
def get_rag_service() -> RAGService:
    return RAGService()


@lru_cache
def get_answer_reviser() -> AnswerReviser:
    return AnswerReviser()


@lru_cache
def get_report_generator() -> ReportGenerator:
    return ReportGenerator(session_store=get_session_store())


@lru_cache
def get_analysis_pipeline() -> AnalysisPipeline:
    rag_service = get_rag_service()
    return AnalysisPipeline(
        job_scraper=JobScraper(),
        resume_parser=ResumeParser(),
        company_research_service=CompanyResearchService(),
        rag_service=rag_service,
        question_generator=QuestionGenerator(),
        answer_drafter=AnswerDrafter(rag_service=rag_service),
    )
