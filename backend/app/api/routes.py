from uuid import uuid4

from fastapi import APIRouter

from app.config import settings
from app.schemas import AnalysisRequest, AnalysisResponse, AnalysisStatus, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name)


@router.post("/analysis", response_model=AnalysisResponse)
async def create_analysis(request: AnalysisRequest) -> AnalysisResponse:
    # TODO: Wire this endpoint into resume parsing, job scraping, LangGraph, RAG,
    # guardrails, human review state, and final report generation.
    return AnalysisResponse(
        session_id=str(uuid4()),
        status=AnalysisStatus.queued,
        message="Analysis request accepted. Full workflow implementation is pending.",
        metadata={"job_url": str(request.job_url), "has_resume_text": bool(request.resume_text)},
    )
