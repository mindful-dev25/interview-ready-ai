from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_report_generator, get_session_store
from app.api.session_helpers import load_session_or_404
from app.schemas import AnalysisStatus, FinalReportResponse, HumanReviewStatus, InterviewAnswer, SessionState
from app.services.report_generator import REPORT_FORMAT_VERSION, REVIEWED_STATUSES, ReportGenerator
from app.services.report_markdown import tidy_report_markdown
from app.storage.session_store import SessionStore

router = APIRouter(tags=["report"])


def _reviewed_answers(session: SessionState) -> list[InterviewAnswer]:
    return [answer for answer in session.answers if answer.human_status in REVIEWED_STATUSES]


def _report_inputs(answers: list[InterviewAnswer]) -> list[tuple[str, str]]:
    """What a report is built from: each reviewed answer's id and final text."""
    return [(answer.id, answer.final_answer or answer.draft_answer) for answer in answers]


@router.get("/report/{session_id}", response_model=FinalReportResponse)
async def get_final_report(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
    report_generator: ReportGenerator = Depends(get_report_generator),
) -> FinalReportResponse:
    session = await load_session_or_404(store, session_id)
    reviewed = _reviewed_answers(session)

    cached = session.final_report
    # A saved report is reused only while the answers it was built from are unchanged and its
    # layout is current; after a revision, edit, or re-approval it is rebuilt from the current answers.
    if (
        cached is not None
        and cached.format_version == REPORT_FORMAT_VERSION
        and _report_inputs(cached.approved_answers) == _report_inputs(reviewed)
    ):
        # Reports saved before the tidy step existed may still hold tables; tidying is safe to repeat.
        return cached.model_copy(update={"report_markdown": tidy_report_markdown(cached.report_markdown)})

    if session.status != AnalysisStatus.complete:
        raise HTTPException(
            status_code=409,
            detail="Final report is available after all answers are reviewed.",
        )

    try:
        report_body = await report_generator.generate(session)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    final_report = FinalReportResponse(
        session_id=session_id,
        status=session.status,
        message="Final report generated successfully.",
        report_markdown=report_body,
        approved_answers=reviewed,
        outstanding_reviews=[a.id for a in session.answers if a.human_status == HumanReviewStatus.needs_revision],
        format_version=REPORT_FORMAT_VERSION,
    )
    # update() merges into the stored session, so changes made during generation are kept.
    await store.update(session_id, {"final_report": final_report})
    return final_report
