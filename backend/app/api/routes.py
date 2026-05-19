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
    RevisionRequest,
    RevisionResponse,
    SessionState,
)
from app.core.llm import LLMConfigurationError
from app.services.answer_reviser import AnswerReviser
from app.services.report_generator import ReportGenerator
from app.storage.session_store import SessionStore

router = APIRouter()
session_store = SessionStore()
report_generator = ReportGenerator()
answer_reviser = AnswerReviser()


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
            question="Tell me about yourself.",
            category="introduction",
            difficulty="easy",
            rationale="Opens the interview and sets the tone; tests communication and self-awareness.",
            related_requirements=["communication", "self-awareness"],
        ),
        InterviewQuestion(
            id="q2",
            question="Why are you interested in this role?",
            category="motivation",
            difficulty="easy",
            rationale="Reveals alignment between the candidate's goals and the role.",
            related_requirements=["motivation", "role fit"],
        ),
        InterviewQuestion(
            id="q3",
            question="Tell me about a time you solved a hard technical problem.",
            category="behavioral",
            difficulty="medium",
            rationale="Evaluates problem-solving depth and communication of technical work.",
            related_requirements=["problem solving", "technical ownership"],
        ),
        InterviewQuestion(
            id="q4",
            question="How would you prioritize competing deadlines on this role?",
            category="strategy",
            difficulty="medium",
            rationale="Assesses planning, time management, and stakeholder communication.",
            related_requirements=["project management", "focus"],
        ),
        InterviewQuestion(
            id="q5",
            question="Describe a project you're most proud of and your specific contribution.",
            category="behavioral",
            difficulty="medium",
            rationale="Surfaces ownership, impact, and the candidate's sense of quality.",
            related_requirements=["ownership", "impact", "engineering quality"],
        ),
        InterviewQuestion(
            id="q6",
            question="Tell me about a time you disagreed with a teammate or manager. How did you handle it?",
            category="behavioral",
            difficulty="medium",
            rationale="Tests interpersonal skills, professional maturity, and conflict resolution.",
            related_requirements=["collaboration", "communication", "maturity"],
        ),
        InterviewQuestion(
            id="q7",
            question="How do you approach learning a new technology or codebase quickly?",
            category="growth",
            difficulty="easy",
            rationale="Signals learning agility and resourcefulness, important in fast-moving teams.",
            related_requirements=["learning agility", "adaptability"],
        ),
        InterviewQuestion(
            id="q8",
            question="Describe a situation where you had to deliver under tight constraints. What trade-offs did you make?",
            category="behavioral",
            difficulty="hard",
            rationale="Probes judgment under pressure and ability to reason about trade-offs explicitly.",
            related_requirements=["decision making", "delivery", "pragmatism"],
        ),
        InterviewQuestion(
            id="q9",
            question="What does good code quality mean to you, and how do you maintain it day to day?",
            category="technical",
            difficulty="medium",
            rationale="Reveals engineering standards and whether the candidate can articulate quality practices.",
            related_requirements=["engineering quality", "code review", "testing"],
        ),
        InterviewQuestion(
            id="q10",
            question="Tell me about a time a project didn't go as planned. What happened and what did you learn?",
            category="behavioral",
            difficulty="medium",
            rationale="Tests resilience, honesty, and the ability to extract lessons from failure.",
            related_requirements=["resilience", "accountability", "growth mindset"],
        ),
        InterviewQuestion(
            id="q11",
            question="How do you collaborate with non-technical stakeholders to define requirements?",
            category="collaboration",
            difficulty="medium",
            rationale="Evaluates cross-functional communication and ability to translate between technical and business perspectives.",
            related_requirements=["communication", "product sense", "collaboration"],
        ),
        InterviewQuestion(
            id="q12",
            question="Where do you see yourself in three years, and how does this role fit into that path?",
            category="motivation",
            difficulty="easy",
            rationale="Gauges ambition, self-awareness, and whether the candidate's trajectory aligns with the team.",
            related_requirements=["career growth", "role fit"],
        ),
        InterviewQuestion(
            id="q13",
            question="What questions do you have for us?",
            category="candidate_questions",
            difficulty="easy",
            rationale="Reveals curiosity, preparation, and what the candidate values in a role and team.",
            related_requirements=["curiosity", "preparation"],
        ),
    ]

    answers = [
        InterviewAnswer(
            id="a1",
            question=questions[0],
            draft_answer=(
                "I'm a software engineer with several years of experience building backend services and APIs. "
                "I enjoy working on problems that sit at the intersection of engineering and product — "
                "where clean architecture and user impact both matter. "
                "Most recently I've been focused on AI-enabled tools, and I'm drawn to roles where I can ship "
                "things that users rely on daily."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a2",
            question=questions[1],
            draft_answer=(
                "I'm excited about this role because it combines the technical challenges I enjoy — "
                "scalable APIs, LLM integration, and reliable data pipelines — with a product that solves "
                "a real problem. I've been following the space closely, and I believe this team is approaching "
                "the problem in a thoughtful way that I'd like to be part of."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a3",
            question=questions[2],
            draft_answer=(
                "I solved a hard technical problem by breaking it into smaller pieces, "
                "validating each part, and collaborating with stakeholders to ensure alignment. "
                "I then iterated on the solution until it met performance and quality goals."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a4",
            question=questions[3],
            draft_answer=(
                "I prioritize work by impact and urgency, mapping deadlines against business goals. "
                "I communicate trade-offs early and adjust as needed when new information arrives."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a5",
            question=questions[4],
            draft_answer=(
                "One project I'm most proud of is a real-time data pipeline I led from design to production. "
                "My specific contribution was the schema evolution strategy that allowed us to deploy "
                "breaking changes without downtime. It became the standard approach the team reused across "
                "three subsequent services."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a6",
            question=questions[5],
            draft_answer=(
                "I once disagreed with my manager about releasing a feature before proper load testing. "
                "Rather than escalating, I prepared a short risk summary with concrete numbers and requested "
                "a 30-minute discussion. We agreed on a limited rollout to 5% of users first. "
                "That turned out to be the right call — we caught a cache invalidation bug before it hit everyone."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a7",
            question=questions[6],
            draft_answer=(
                "I start by reading the official docs and running the quickstart to build a mental model. "
                "Then I look at existing production usage in the codebase to understand the team's conventions. "
                "I ask specific questions when I'm stuck rather than spending too long in isolation, "
                "and I write a short internal note summarizing what I learned so others benefit too."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a8",
            question=questions[7],
            draft_answer=(
                "During a hard deadline, I had to choose between full test coverage and shipping on time. "
                "I covered the critical paths with integration tests and filed explicit tech-debt tickets for "
                "the rest, with acceptance criteria already written. I communicated the risk to the team "
                "before merging so no one was surprised later."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a9",
            question=questions[8],
            draft_answer=(
                "Good code quality means the next engineer can understand, change, and test it confidently. "
                "Day to day I maintain that by writing tests before I consider something done, "
                "keeping PRs small and focused, and giving code reviews that explain the 'why' not just the 'what'. "
                "I also treat linter and type-checker warnings as errors, not suggestions."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a10",
            question=questions[9],
            draft_answer=(
                "A migration project I led ran two weeks over because I underestimated the complexity of "
                "the legacy data model. The lesson was to timebox exploration spikes before committing to an estimate. "
                "Since then I always include a discovery phase in my project plans and flag uncertainty ranges "
                "explicitly rather than giving a single number."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a11",
            question=questions[10],
            draft_answer=(
                "I schedule short discovery sessions with stakeholders before writing any code, "
                "focusing on the outcome they need rather than the feature they're describing. "
                "I use lightweight artifacts like user story maps or acceptance criteria tables "
                "to validate shared understanding, and I check in at a mid-point so surprises surface "
                "early rather than at delivery."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a12",
            question=questions[11],
            draft_answer=(
                "In three years I'd like to be a strong technical lead — someone who can scope large "
                "projects, mentor junior engineers, and contribute to architectural decisions. "
                "This role fits that path because it gives me the scope to own meaningful systems "
                "and work closely with a senior team I can learn from."
            ),
            evidence_used=[],
            human_status=HumanReviewStatus.pending,
        ),
        InterviewAnswer(
            id="a13",
            question=questions[12],
            draft_answer=(
                "A few questions I'd love to explore: "
                "What does the onboarding experience look like for the first 90 days? "
                "How does the team balance feature work with technical debt? "
                "What does success look like for this role in the first six months? "
                "And what's the biggest challenge the team is working through right now?"
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


@router.post("/revision", response_model=RevisionResponse)
async def revise_answer(request: RevisionRequest) -> RevisionResponse:
    state = await session_store.load(request.session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")

    session = SessionState.model_validate(state)
    answer = next((item for item in session.answers if item.id == request.answer_id), None)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found for the requested session.")

    if not request.reviewer_notes.strip():
        raise HTTPException(status_code=400, detail="reviewer_notes is required to request a revision.")

    try:
        revised_text = await answer_reviser.revise(answer, request.reviewer_notes)
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM not configured: {exc} — set GROQ_API_KEY and GROQ_CHAT_MODEL in backend/.env and restart the server.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM revision failed: {exc}") from exc

    answer.draft_answer = revised_text
    answer.human_status = HumanReviewStatus.pending
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

    return RevisionResponse(
        session_id=request.session_id,
        answer_id=answer.id,
        human_status=answer.human_status,
        message="Answer revised by AI. Please review the updated draft.",
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
