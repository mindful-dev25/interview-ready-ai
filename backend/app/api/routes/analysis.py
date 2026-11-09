from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_analysis_pipeline, get_session_store
from app.api.session_helpers import load_session_or_404
from app.schemas import AnalysisRequest, AnalysisResponse, SessionState
from app.services.analysis_pipeline import AnalysisPipeline
from app.services.job_scraper import JobFetchError
from app.storage.session_store import SessionStore

router = APIRouter(tags=["analysis"])


@router.post("/analysis", response_model=AnalysisResponse)
async def create_analysis(
    request: AnalysisRequest,
    pipeline: AnalysisPipeline = Depends(get_analysis_pipeline),
    store: SessionStore = Depends(get_session_store),
) -> AnalysisResponse:
    session_id = str(uuid4())
    try:
        state = await pipeline.run(session_id, request)
    except JobFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    await store.save(session_id, state)

    return AnalysisResponse(
        session_id=session_id,
        status=state.status,
        message="Draft answers are ready for review.",
        questions=state.questions,
        answers=state.answers,
        next_action="review_answers",
        metadata=state.metadata,
    )


@router.get("/analysis/{session_id}", response_model=SessionState)
async def get_analysis(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
) -> SessionState:
    return await load_session_or_404(store, session_id)
