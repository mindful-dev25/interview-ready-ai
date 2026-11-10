from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_report_generator, get_session_store
from app.api.session_helpers import load_session_or_404
from app.schemas import AnalysisStatus, FinalReportResponse, HumanReviewStatus
from app.services.report_generator import REVIEWED_STATUSES, ReportGenerator
from app.storage.session_store import SessionStore

router = APIRouter(tags=["report"])


@router.get("/report/{session_id}", response_model=FinalReportResponse)
async def get_final_report(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
    report_generator: ReportGenerator = Depends(get_report_generator),
) -> FinalReportResponse:
    session = await load_session_or_404(store, session_id)

    if session.final_report is not None:
        return session.final_report

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
        approved_answers=[a for a in session.answers if a.human_status in REVIEWED_STATUSES],
        outstanding_reviews=[a.id for a in session.answers if a.human_status == HumanReviewStatus.needs_revision],
    )
    # update() merges into the stored session, so changes made during generation are kept.
    await store.update(session_id, {"final_report": final_report})
    return final_report
