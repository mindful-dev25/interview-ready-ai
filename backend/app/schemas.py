from enum import Enum
from typing import Any

from pydantic import BaseModel, HttpUrl


class AnalysisStatus(str, Enum):
    queued = "queued"
    running = "running"
    needs_review = "needs_review"
    complete = "complete"
    failed = "failed"


class HealthResponse(BaseModel):
    status: str
    app_name: str


class AnalysisRequest(BaseModel):
    job_url: HttpUrl
    resume_text: str | None = None


class EvidenceItem(BaseModel):
    source: str
    quote: str
    relevance: str


class InterviewAnswer(BaseModel):
    question: str
    answer: str
    guardrail_notes: list[str] = []
    evidence: list[EvidenceItem] = []


class AnalysisResponse(BaseModel):
    session_id: str
    status: AnalysisStatus
    message: str
    answers: list[InterviewAnswer] = []
    metadata: dict[str, Any] = {}
