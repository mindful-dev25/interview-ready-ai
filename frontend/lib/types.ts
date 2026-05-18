export type AnalysisStatus = "queued" | "running" | "needs_review" | "complete" | "failed";

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
  category?: string;
  difficulty?: string;
  rationale?: string;
};

export type InterviewAnswer = {
  id: string;
  question: InterviewQuestion;
  draft_answer: string;
  final_answer?: string;
  human_status?: "pending" | "approved" | "edited" | "needs_revision";
  evidence_used?: EvidenceItem[];
  truthfulness_guardrail?: {
    unsupported_claims?: string[];
    claims?: Array<{ explanation?: string }>;
  };
  citation_guardrail?: {
    weak_citation_notes?: string[];
    missing_citation_claims?: string[];
  };
};

export type AnalysisResponse = {
  sessionId: string;
  status: AnalysisStatus;
  message: string;
  questions?: InterviewQuestion[];
  answers: InterviewAnswer[];
  next_action?: string;
};

export type ReviewResponse = {
  session_id: string;
  answer_id: string;
  human_status: string;
  message: string;
  answer?: InterviewAnswer;
};

export type FinalReportResponse = {
  session_id: string;
  status: AnalysisStatus;
  message: string;
  report_markdown: string;
};
