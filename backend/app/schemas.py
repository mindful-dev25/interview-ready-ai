from enum import Enum
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisStatus(str, Enum):
    queued = "queued"
    running = "running"
    needs_review = "needs_review"
    complete = "complete"
    failed = "failed"


class HumanReviewStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    edited = "edited"
    needs_revision = "needs_revision"


class ReviewAction(str, Enum):
    approve = "approve"
    edit = "edit"
    request_revision = "request_revision"


class EvidenceSourceType(str, Enum):
    resume = "resume"
    job_description = "job_description"
    company_research = "company_research"
    generated = "generated"


class HealthResponse(BaseModel):
    status: str
    app_name: str


class AnalyzeRequestMetadata(BaseModel):
    user_id: str | None = None
    target_role: str | None = None
    target_company: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    job_url: str
    resume_text: str | None = None
    resume_filename: str | None = None
    metadata: AnalyzeRequestMetadata = Field(default_factory=AnalyzeRequestMetadata)


class EvidenceItem(BaseModel):
    id: str
    source_type: EvidenceSourceType
    source: str
    quote: str
    relevance: str
    source_url: HttpUrl | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobRequirements(BaseModel):
    source_url: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    summary: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    raw_text: str | None = None


class CompanyResearch(BaseModel):
    company_name: str | None = None
    website: HttpUrl | None = None
    summary: str | None = None
    products: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    recent_highlights: list[str] = Field(default_factory=list)
    interview_signals: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    id: str
    question: str
    category: str | None = None
    difficulty: str | None = None
    rationale: str | None = None
    related_requirements: list[str] = Field(default_factory=list)


class GuardrailClaim(BaseModel):
    claim: str
    supported: bool = False
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str | None = None
    severity: str = "medium"
    suggested_fix: str | None = None


class TruthfulnessGuardrailResult(BaseModel):
    passed: bool = False
    score: float | None = None
    summary: str | None = None
    claims: list[GuardrailClaim] = Field(default_factory=list)
    unsupported_claims: list[GuardrailClaim] = Field(default_factory=list)


class CitationGuardrailResult(BaseModel):
    passed: bool = False
    summary: str | None = None
    cited_evidence_ids: list[str] = Field(default_factory=list)
    missing_citation_claims: list[str] = Field(default_factory=list)
    weak_citation_notes: list[str] = Field(default_factory=list)


class InterviewAnswer(BaseModel):
    id: str
    question: InterviewQuestion
    draft_answer: str = ""
    final_answer: str | None = None
    evidence_used: list[EvidenceItem] = Field(default_factory=list)
    truthfulness_guardrail: TruthfulnessGuardrailResult = Field(
        default_factory=TruthfulnessGuardrailResult
    )
    citation_guardrail: CitationGuardrailResult = Field(default_factory=CitationGuardrailResult)
    human_status: HumanReviewStatus = HumanReviewStatus.pending
    suggested_safe_rewrite: str | None = None
    reviewer_notes: list[str] = Field(default_factory=list)


class FinalReportResponse(BaseModel):
    session_id: str
    status: AnalysisStatus
    message: str
    report_markdown: str = ""
    approved_answers: list[InterviewAnswer] = Field(default_factory=list)
    outstanding_reviews: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class SessionState(BaseModel):
    session_id: str
    status: AnalysisStatus = AnalysisStatus.queued
    request: AnalyzeRequest | None = None
    job_requirements: JobRequirements | None = None
    company_research: CompanyResearch | None = None
    questions: list[InterviewQuestion] = Field(default_factory=list)
    answers: list[InterviewAnswer] = Field(default_factory=list)
    final_report: FinalReportResponse | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyzeResponse(BaseModel):
    session_id: str
    status: AnalysisStatus
    message: str
    questions: list[InterviewQuestion] = Field(default_factory=list)
    answers: list[InterviewAnswer] = Field(default_factory=list)
    next_action: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewActionRequest(BaseModel):
    session_id: str
    answer_id: str
    action: ReviewAction
    edited_answer: str | None = None
    reviewer_notes: str | None = None


class ReviewActionResponse(BaseModel):
    session_id: str
    answer_id: str
    human_status: HumanReviewStatus
    message: str
    answer: InterviewAnswer | None = None


class RevisionRequest(BaseModel):
    session_id: str
    answer_id: str
    reviewer_notes: str


class RevisionResponse(BaseModel):
    session_id: str
    answer_id: str
    human_status: HumanReviewStatus
    message: str
    answer: InterviewAnswer


AnalysisRequest = AnalyzeRequest
AnalysisResponse = AnalyzeResponse
