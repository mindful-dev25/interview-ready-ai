"""Human-in-the-loop review of drafted answers: approve / edit / request revision."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_answer_reviser, get_session_store
from app.api.session_helpers import find_answer_or_404, load_session_or_404, save_session
from app.core.llm import LLMConfigurationError
from app.schemas import (
    CitationGuardrailResult,
    HumanReviewStatus,
    ReviewAction,
    ReviewActionRequest,
    ReviewActionResponse,
    RevisionRequest,
    RevisionResponse,
    TruthfulnessGuardrailResult,
)
from app.services.answer_reviser import AnswerReviser
from app.storage.session_store import SessionStore

router = APIRouter(tags=["review"])


@router.post("/review", response_model=ReviewActionResponse)
async def review_answer(
    request: ReviewActionRequest,
    store: SessionStore = Depends(get_session_store),
) -> ReviewActionResponse:
    session = await load_session_or_404(store, request.session_id)
    answer = find_answer_or_404(session, request.answer_id)

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

    await save_session(store, session)

    return ReviewActionResponse(
        session_id=request.session_id,
        answer_id=answer.id,
        human_status=answer.human_status,
        message=message,
        answer=answer,
        session_status=session.status,
    )


@router.post("/revision", response_model=RevisionResponse)
async def revise_answer(
    request: RevisionRequest,
    store: SessionStore = Depends(get_session_store),
    reviser: AnswerReviser = Depends(get_answer_reviser),
) -> RevisionResponse:
    session = await load_session_or_404(store, request.session_id)
    answer = find_answer_or_404(session, request.answer_id)

    if not request.reviewer_notes.strip():
        raise HTTPException(status_code=400, detail="reviewer_notes is required to request a revision.")

    try:
        revised_text = await reviser.revise(answer, request.reviewer_notes)
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM not configured: {exc} — set GROQ_API_KEY and GROQ_CHAT_MODEL in backend/.env and restart the server.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM revision failed: {exc}") from exc

    # The LLM call above takes seconds. Reload so reviews of other answers made
    # in the meantime are kept instead of being overwritten by a stale copy.
    session = await load_session_or_404(store, request.session_id)
    answer = find_answer_or_404(session, request.answer_id)

    answer.draft_answer = revised_text
    answer.final_answer = None
    answer.human_status = HumanReviewStatus.pending
    answer.reviewer_notes.append(request.reviewer_notes)
    # The earlier guardrail findings described the previous draft.
    answer.truthfulness_guardrail = TruthfulnessGuardrailResult()
    answer.citation_guardrail = CitationGuardrailResult()
    answer.suggested_safe_rewrite = None

    await save_session(store, session)

    return RevisionResponse(
        session_id=request.session_id,
        answer_id=answer.id,
        human_status=answer.human_status,
        message="Answer revised by AI. Please review the updated draft.",
        answer=answer,
        session_status=session.status,
    )
