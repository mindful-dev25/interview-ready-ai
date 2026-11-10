// Mirrors the response models in backend/app/schemas.py. Field names match the API's JSON.

export type AnalysisStatus = "queued" | "running" | "needs_review" | "complete" | "failed";

export type HumanReviewStatus = "pending" | "approved" | "edited" | "needs_revision";

export type ReviewAction = "approve" | "edit" | "request_revision";

export type EvidenceItem = {
  id?: string;
  source?: string;
  source_type?: string;
  quote: string;
  relevance?: string;
};

export type InterviewQuestion = {
  id: string;
  question: string;
  category?: string | null;
  difficulty?: string | null;
  rationale?: string | null;
};

export type GuardrailClaim = {
  claim: string;
  supported: boolean;
  evidence_ids: string[];
  explanation?: string | null;
  severity: string;
  suggested_fix?: string | null;
};

export type TruthfulnessGuardrail = {
  passed: boolean;
  score?: number | null;
  /** Null when the answer has not been checked. */
  summary?: string | null;
  claims: GuardrailClaim[];
  unsupported_claims: GuardrailClaim[];
};

export type CitationGuardrail = {
  passed: boolean;
  summary?: string | null;
  cited_evidence_ids: string[];
  missing_citation_claims: string[];
  weak_citation_notes: string[];
};

export type InterviewAnswer = {
  id: string;
  question: InterviewQuestion;
  draft_answer: string;
  final_answer?: string | null;
  human_status?: HumanReviewStatus;
  evidence_used?: EvidenceItem[];
  truthfulness_guardrail?: TruthfulnessGuardrail;
  citation_guardrail?: CitationGuardrail;
  suggested_safe_rewrite?: string | null;
};

export type AnalysisResponse = {
  session_id: string;
  status: AnalysisStatus;
  message: string;
  questions?: InterviewQuestion[];
  answers: InterviewAnswer[];
  next_action?: string | null;
  metadata?: {
    /** Steps that fell back to generic behavior, e.g. an unreachable job posting. */
    warnings?: string[];
  };
};

export type ReviewResponse = {
  session_id: string;
  answer_id: string;
  human_status: HumanReviewStatus;
  message: string;
  answer?: InterviewAnswer | null;
  session_status?: AnalysisStatus | null;
};

export type RevisionResponse = {
  session_id: string;
  answer_id: string;
  human_status: HumanReviewStatus;
  message: string;
  answer: InterviewAnswer;
  session_status?: AnalysisStatus | null;
};

export type ResumeTextResponse = {
  text: string;
  filename?: string | null;
  page_count: number;
};

export type FinalReportResponse = {
  session_id: string;
  status: AnalysisStatus;
  message: string;
  report_markdown: string;
};
