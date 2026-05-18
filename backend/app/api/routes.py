from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    FinalReportResponse,
    HealthResponse,
    HumanReviewStatus,
    InterviewAnswer,
    InterviewQuestion,
    JobRequirements,
    CompanyResearch,
    ReviewAction,
    ReviewActionRequest,
    ReviewActionResponse,
    SessionState,
)
from app.services.report_generator import ReportGenerator
from app.storage.session_store import SessionStore

router = APIRouter()
session_store = SessionStore()
report_generator = ReportGenerator()


def _session_status_from_answers(answers: list[InterviewAnswer]) -> AnalysisStatus:
    if any(
        answer.human_status in (HumanReviewStatus.pending, HumanReviewStatus.needs_revision)
        for answer in answers
    ):
        return AnalysisStatus.needs_review
    return AnalysisStatus.complete


def _build_analysis_state(session_id: str, request: AnalysisRequest) -> SessionState:
    questions = [
        InterviewQuestion(
            id="q1",
            question="Tell me about a time you solved a hard technical problem.",
            category="behavioral",
            difficulty="medium",
            rationale="Evaluates problem-solving and communication skills.",
            related_requirements=["problem solving", "technical ownership"],
        ),
        InterviewQuestion(
            id="q2",
            question="How would you prioritize competing deadlines on this role?",
            category="strategy",
            difficulty="medium",
            rationale="Assesses planning and time management.",
            related_requirements=["project management", "focus"],
        ),
    ]

    answers = [
        InterviewAnswer(
            id="a1",
            question=questions[0],
            draft_answer=(
                "I solved a hard technical problem by breaking it into smaller pieces, "
                "validating each part, and collaborating with stakeholders to ensure alignment. "
                "I then iterated on the solution until it met performance and quality goals."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a2",
            question=questions[1],
            draft_answer=(
                "I prioritize work by impact and urgency, mapping deadlines against business goals. "
                "I communicate tradeoffs early and adjust as needed when new information arrives."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
    ]

    job_requirements = JobRequirements(
        source_url=request.job_url,
        title="Software Engineer",
        company=request.metadata.target_company or "Target Company",
        location="Remote",
        employment_type="Full-time",
        seniority="Mid-level",
        summary="A role focused on building reliable AI-enabled products and supporting end-to-end delivery.",
        responsibilities=[
            "Design and ship high-quality software",
            "Collaborate with cross-functional teams",
            "Translate product goals into technical execution",
        ],
        required_skills=["Python", "APIs", "problem solving"],
        preferred_skills=["LLMs", "RAG", "team leadership"],
        keywords=["AI", "interview preparation", "software engineering"],
    )

    company_research = CompanyResearch(
        company_name=request.metadata.target_company or "Target Company",
        website=request.job_url,
        summary=(
            "This company is building intelligent products that help people prepare for interviews. "
            "They value user empathy, clarity, and practical engineering." 
        ),
        products=["Interview coach", "candidate workspace"],
        values=["customer-centricity", "ownership", "impact"],
        recent_highlights=["Expanded its interview prep platform", "Published a new AI assistant"],
        interview_signals=["behavioral questions", "case-style prompts"],
    )

    metadata = {
        "job_url": str(request.job_url),
        "has_resume_text": bool(request.resume_text),
    }

    return SessionState(
        session_id=session_id,
        status=AnalysisStatus.needs_review,
        request=request,
        job_requirements=job_requirements,
        company_research=company_research,
        questions=questions,
        answers=answers,
        metadata=metadata,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name)


@router.post("/analysis", response_model=AnalysisResponse)
async def create_analysis(request: AnalysisRequest) -> AnalysisResponse:
    session_id = str(uuid4())
    initial_state = _build_analysis_state(session_id, request)
    await session_store.save(session_id, initial_state)

    return AnalysisResponse(
        session_id=session_id,
        status=initial_state.status,
        message="Draft answers are ready and need review.",
        questions=initial_state.questions,
        answers=initial_state.answers,
        next_action="review_answers",
        metadata=initial_state.metadata,
    )


@router.get("/analysis/{session_id}", response_model=SessionState)
async def get_analysis(session_id: str) -> SessionState:
    state = await session_store.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    return SessionState.model_validate(state)


@router.post("/review", response_model=ReviewActionResponse)
async def review_answer(request: ReviewActionRequest) -> ReviewActionResponse:
    state = await session_store.load(request.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")

    session = SessionState.model_validate(state)
    answer = next((item for item in session.answers if item.id == request.answer_id), None)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found for the requested session.")

    if request.action == ReviewAction.approve:
        answer.human_status = HumanReviewStatus.approved
        answer.final_answer = answer.draft_answer
        message = "Answer approved."
    elif request.action == ReviewAction.edit:
        if not request.edited_answer:
            raise HTTPException(status_code=400, detail="edited_answer is required for edit actions.")
        answer.human_status = HumanReviewStatus.edited
        answer.final_answer = request.edited_answer
        message = "Answer edited and marked as reviewed."
    else:
        answer.human_status = HumanReviewStatus.needs_revision
        message = "Revision requested for this answer."

    if request.reviewer_notes:
        answer.reviewer_notes.append(request.reviewer_notes)

    updated_status = _session_status_from_answers(session.answers)
    session.status = updated_status

    await session_store.update(
        request.session_id,
        {
            "answers": session.answers,
            "status": session.status,
        },
    )

    return ReviewActionResponse(
        session_id=request.session_id,
        answer_id=answer.id,
        human_status=answer.human_status,
        message=message,
        answer=answer,
    )


@router.get("/report/{session_id}", response_model=FinalReportResponse)
async def get_final_report(session_id: str) -> FinalReportResponse:
    state = await session_store.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")

    session = SessionState.model_validate(state)
    if session.final_report is None:
        if session.status != AnalysisStatus.complete:
            raise HTTPException(
                status_code=409,
                detail="Final report is available after all answers are reviewed.",
            )

        report_body = await report_generator.generate(session_id)
        final_report = FinalReportResponse(
            session_id=session_id,
            status=session.status,
            message="Final report generated successfully.",
            report_markdown=report_body,
            approved_answers=[answer for answer in session.answers if answer.human_status in (HumanReviewStatus.approved, HumanReviewStatus.edited)],
            outstanding_reviews=[answer.id for answer in session.answers if answer.human_status == HumanReviewStatus.needs_revision],
        )
        await session_store.update(session_id, {"final_report": final_report})
        return final_report

    return FinalReportResponse.model_validate(session.final_report)
