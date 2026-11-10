"""Helpers shared by routes that read and update a stored analysis session."""

from fastapi import HTTPException

from app.schemas import AnalysisStatus, HumanReviewStatus, InterviewAnswer, SessionState
from app.storage.session_store import SessionStore


async def load_session_or_404(store: SessionStore, session_id: str) -> SessionState:
    state = await store.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    return SessionState.model_validate(state)


def find_answer_or_404(session: SessionState, answer_id: str) -> InterviewAnswer:
    answer = next((item for item in session.answers if item.id == answer_id), None)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found for the requested session.")
    return answer


def session_status_from_answers(answers: list[InterviewAnswer]) -> AnalysisStatus:
    if any(
        answer.human_status in (HumanReviewStatus.pending, HumanReviewStatus.needs_revision)
        for answer in answers
    ):
        return AnalysisStatus.needs_review
    return AnalysisStatus.complete


async def save_session(store: SessionStore, session: SessionState) -> None:
    """Recompute the session status from its answers and persist the session.

    Call this without awaiting anything slow between loading the session and
    saving it: a session loaded before a long ``await`` may be stale, and saving
    it would overwrite changes made in the meantime.
    """
    session.status = session_status_from_answers(session.answers)
    await store.save(session.session_id, session)
