from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.schemas import AnalysisRequest, AnalysisResponse, AnalysisStatus, HealthResponse
from app.storage.session_store import SessionStore

router = APIRouter()
session_store = SessionStore()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name)


@router.post("/analysis", response_model=AnalysisResponse)
async def create_analysis(request: AnalysisRequest) -> AnalysisResponse:
    # TODO: Wire this endpoint into resume parsing, job scraping, LangGraph, RAG,
    # guardrails, human review state, and final report generation.
    session_id = str(uuid4())
    metadata = {
        "job_url": str(request.job_url),
        "has_resume_text": bool(request.resume_text),
    }
    await session_store.save(
        session_id,
        {
            "status": AnalysisStatus.queued,
            "request": request,
            "metadata": metadata,
        },
    )
    return AnalysisResponse(
        session_id=session_id,
        status=AnalysisStatus.queued,
        message="Analysis request accepted. Full workflow implementation is pending.",
        metadata=metadata,
    )


@router.get("/analysis/{session_id}")
async def get_analysis(session_id: str) -> dict[str, Any]:
    state = await session_store.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Analysis session not found.")
    return state
