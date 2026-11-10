"""Shared service instances for the API layer, injected via FastAPI ``Depends``.

Each getter is cached so the whole app shares one instance. Tests can swap any of
them with ``app.dependency_overrides[get_x] = lambda: fake``.
"""

from functools import lru_cache

from app.core.llm import LLMClient
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.answer_drafter import AnswerDrafter
from app.services.answer_reviser import AnswerReviser
from app.services.company_research import CompanyResearchService
from app.services.guardrails import GuardrailService
from app.services.job_scraper import JobScraper
from app.services.question_generator import QuestionGenerator
from app.services.rag import RAGService
from app.services.report_generator import ReportGenerator
from app.services.resume_parser import ResumeParser
from app.storage.session_store import SessionStore


@lru_cache
def get_llm_client() -> LLMClient:
    """One client for every service, so they all reuse the same pooled connection."""
    return LLMClient()


@lru_cache
def get_session_store() -> SessionStore:
    return SessionStore()


@lru_cache
def get_rag_service() -> RAGService:
    return RAGService()


@lru_cache
def get_answer_reviser() -> AnswerReviser:
    return AnswerReviser(llm_client=get_llm_client())


@lru_cache
def get_report_generator() -> ReportGenerator:
    return ReportGenerator(llm_client=get_llm_client())


@lru_cache
def get_analysis_pipeline() -> AnalysisPipeline:
    llm = get_llm_client()
    rag_service = get_rag_service()
    return AnalysisPipeline(
        job_scraper=JobScraper(llm_client=llm),
        resume_parser=ResumeParser(llm_client=llm),
        company_research_service=CompanyResearchService(llm_client=llm),
        rag_service=rag_service,
        question_generator=QuestionGenerator(llm_client=llm),
        answer_drafter=AnswerDrafter(
            rag_service=rag_service,
            llm_client=llm,
            guardrails=GuardrailService(llm_client=llm),
        ),
    )
