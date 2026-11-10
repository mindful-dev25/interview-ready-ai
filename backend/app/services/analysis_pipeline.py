"""End-to-end analysis pipeline: job posting + resume -> reviewed-ready interview prep."""

import asyncio
import logging
import re
from typing import Any

from pydantic import HttpUrl, TypeAdapter

from app.schemas import (
    AnalysisRequest,
    AnalysisStatus,
    CompanyResearch,
    HumanReviewStatus,
    InterviewAnswer,
    InterviewQuestion,
    JobRequirements,
    SessionState,
)
from app.services.answer_drafter import AnswerDrafter
from app.services.company_research import CompanyResearchService
from app.services.context_documents import build_context_documents
from app.services.default_questions import fallback_questions, wrap_with_standard_questions
from app.services.job_scraper import JobScraper
from app.services.question_generator import QuestionGenerator
from app.services.rag import RAGService
from app.services.resume_parser import ResumeParser

logger = logging.getLogger(__name__)

_http_url_adapter = TypeAdapter(HttpUrl)


def normalize_job_url(raw: str) -> str:
    url = raw.strip()
    if url and not re.match(r"^https?://", url, re.IGNORECASE):
        url = f"https://{url}"
    return url


def safe_url(raw: str) -> HttpUrl | None:
    if not raw or not raw.strip():
        return None
    try:
        return _http_url_adapter.validate_python(raw.strip())
    except Exception:
        return None


class AnalysisPipeline:
    """Orchestrates scraping, parsing, research, indexing, question generation and drafting.

    Every step degrades gracefully: a failed step is logged and replaced by a
    generic fallback, and user-relevant fallbacks are reported in ``metadata["warnings"]``.
    """

    def __init__(
        self,
        job_scraper: JobScraper,
        resume_parser: ResumeParser,
        company_research_service: CompanyResearchService,
        rag_service: RAGService,
        question_generator: QuestionGenerator,
        answer_drafter: AnswerDrafter,
    ) -> None:
        self.job_scraper = job_scraper
        self.resume_parser = resume_parser
        self.company_research_service = company_research_service
        self.rag_service = rag_service
        self.question_generator = question_generator
        self.answer_drafter = answer_drafter

    async def run(self, session_id: str, request: AnalysisRequest) -> SessionState:
        job_url = normalize_job_url(request.job_url)
        if not job_url:
            raise ValueError("A job URL is required.")

        # The resume and the job posting are independent, so they are processed concurrently.
        (job_data, company_research), (resume_data, resume_warning) = await asyncio.gather(
            self._load_job(job_url),
            self._parse_resume(request.resume_text),
        )
        job_requirements = self._build_job_requirements(job_url, job_data)

        await self._index_context(session_id, request.resume_text, job_data, job_requirements, company_research)

        questions = await self._generate_questions(resume_data, job_requirements, company_research)
        answers = await self._draft_answers(session_id, questions, request.resume_text)

        return SessionState(
            session_id=session_id,
            status=AnalysisStatus.needs_review,
            request=request,
            job_requirements=job_requirements,
            company_research=company_research,
            questions=questions,
            answers=answers,
            metadata={
                "job_url": job_url,
                "has_resume_text": bool(request.resume_text),
                "company": job_requirements.company,
                "role": job_requirements.title,
                # Shown to the user: steps that fell back to generic behavior.
                "warnings": [w for w in (job_data.get("warning"), resume_warning) if w],
            },
        )

    async def _load_job(self, job_url: str) -> tuple[dict[str, Any], CompanyResearch]:
        job_data = await self.job_scraper.scrape(job_url)
        return job_data, await self._research_company(job_data)

    @staticmethod
    def _build_job_requirements(job_url: str, job_data: dict[str, Any]) -> JobRequirements:
        return JobRequirements(
            source_url=job_url,
            title=job_data.get("title") or None,
            company=job_data.get("company") or None,
            location=job_data.get("location") or None,
            responsibilities=job_data.get("responsibilities", []),
            required_skills=job_data.get("required_skills", []),
            preferred_skills=job_data.get("preferred_skills", []),
            keywords=job_data.get("keywords", []),
            raw_text=job_data.get("raw_text"),
        )

    async def _parse_resume(self, resume_text: str | None) -> tuple[dict[str, Any], str | None]:
        """Return the structured resume and, if parsing fell back, a warning for the user."""
        if not resume_text or not resume_text.strip():
            return {}, None
        try:
            return await self.resume_parser.parse_text(resume_text), None
        except ValueError as exc:
            # Raised for resumes that are too short or unstructured; the message is user-facing.
            return {}, str(exc)
        except Exception:
            logger.warning("Resume parsing failed; continuing without structured resume data.", exc_info=True)
            return {}, "The resume could not be analyzed in detail, so questions may be less tailored."

    async def _research_company(self, job_data: dict[str, Any]) -> CompanyResearch:
        company_name = job_data.get("company") or ""
        if not company_name:
            return CompanyResearch(company_name=None)

        try:
            research_data = await self.company_research_service.research(
                company_name, job_data.get("raw_text", "")
            )
            return CompanyResearch(
                company_name=research_data.get("company_name") or company_name,
                website=safe_url(research_data.get("website", "")),
                summary=research_data.get("summary") or None,
                products=research_data.get("products", []),
                values=research_data.get("values", []),
                recent_highlights=research_data.get("recent_highlights", []),
                interview_signals=research_data.get("interview_signals", []),
            )
        except Exception:
            logger.warning("Company research failed for %r.", company_name, exc_info=True)
            return CompanyResearch(company_name=company_name)

    async def _index_context(
        self,
        session_id: str,
        resume_text: str | None,
        job_data: dict[str, Any],
        job_requirements: JobRequirements,
        company_research: CompanyResearch,
    ) -> None:
        documents = build_context_documents(resume_text, job_data, job_requirements, company_research)
        if not documents:
            return
        try:
            await self.rag_service.index_context(session_id, documents)
        except Exception:
            logger.warning("Indexing context failed; answers will be drafted without evidence.", exc_info=True)

    async def _generate_questions(
        self,
        resume_data: dict[str, Any],
        job_requirements: JobRequirements,
        company_research: CompanyResearch,
    ) -> list[InterviewQuestion]:
        job_req_dict = {
            "title": job_requirements.title,
            "company": job_requirements.company,
            "responsibilities": job_requirements.responsibilities,
            "required_skills": job_requirements.required_skills,
            "preferred_skills": job_requirements.preferred_skills,
            "keywords": job_requirements.keywords,
        }
        company_dict = {
            "company_name": company_research.company_name,
            "summary": company_research.summary,
            "values": company_research.values,
        }

        try:
            generated = await self.question_generator.generate_questions(
                resume_data=resume_data,
                job_requirements=job_req_dict,
                company_research=company_dict,
            )
        except Exception:
            logger.warning("Question generation failed; using fallback questions.", exc_info=True)
            generated = fallback_questions()

        return wrap_with_standard_questions(generated)

    async def _draft_answers(
        self, session_id: str, questions: list[InterviewQuestion], resume_text: str | None
    ) -> list[InterviewAnswer]:
        try:
            return await self.answer_drafter.draft_answers(session_id, questions, resume_text=resume_text)
        except Exception:
            logger.warning("Answer drafting failed; returning empty drafts.", exc_info=True)
            return [
                InterviewAnswer(
                    id=f"a{i + 1}",
                    question=question,
                    draft_answer="",
                    evidence_used=[],
                    human_status=HumanReviewStatus.pending,
                )
                for i, question in enumerate(questions)
            ]
