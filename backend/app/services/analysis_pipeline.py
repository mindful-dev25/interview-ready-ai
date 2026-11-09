"""End-to-end analysis pipeline: job posting + resume -> reviewed-ready interview prep."""

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
from app.services.default_questions import fallback_questions, wrap_with_standard_questions
from app.services.job_scraper import JobScraper
from app.services.question_generator import QuestionGenerator
from app.services.rag import RAGService
from app.services.resume_parser import ResumeParser

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

    Only job scraping is allowed to fail the pipeline; every later step degrades gracefully.
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

        job_data = await self.job_scraper.scrape(job_url)
        job_requirements = self._build_job_requirements(job_url, job_data)
        resume_data = await self._parse_resume(request.resume_text)
        company_research = await self._research_company(job_data)

        await self._index_context(session_id, request.resume_text, job_data, job_requirements, company_research)

        questions = await self._generate_questions(resume_data, job_requirements, company_research)
        answers = await self._draft_answers(session_id, questions)

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
            },
        )

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

    async def _parse_resume(self, resume_text: str | None) -> dict[str, Any]:
        if not resume_text or not resume_text.strip():
            return {}
        try:
            return await self.resume_parser.parse_text(resume_text)
        except Exception:
            return {}

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
            return CompanyResearch(company_name=company_name)

    async def _index_context(
        self,
        session_id: str,
        resume_text: str | None,
        job_data: dict[str, Any],
        job_requirements: JobRequirements,
        company_research: CompanyResearch,
    ) -> None:
        documents: list[dict[str, Any]] = []

        if resume_text and resume_text.strip():
            documents.append({"content": resume_text, "source_type": "resume", "source": "Resume"})

        job_context = "\n".join(filter(None, [
            job_data.get("raw_text", ""),
            *job_data.get("responsibilities", []),
            *job_data.get("required_skills", []),
            *job_data.get("preferred_skills", []),
        ]))
        if job_context.strip():
            role_label = f"{job_requirements.title or 'Role'} at {job_requirements.company or 'Company'}"
            documents.append({"content": job_context, "source_type": "job_description", "source": role_label})

        if company_research.summary:
            company_context = " ".join(filter(None, [
                company_research.summary,
                *company_research.values,
                *company_research.recent_highlights,
            ]))
            source = job_data.get("company") or "Company"
            documents.append({"content": company_context, "source_type": "company_research", "source": source})

        if not documents:
            return
        try:
            await self.rag_service.index_context(session_id, documents)
        except Exception:
            pass

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
            generated = fallback_questions()

        return wrap_with_standard_questions(generated)

    async def _draft_answers(
        self, session_id: str, questions: list[InterviewQuestion]
    ) -> list[InterviewAnswer]:
        try:
            return await self.answer_drafter.draft_answers(session_id, questions)
        except Exception:
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
