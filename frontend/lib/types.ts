export type AnalysisStatus = "queued" | "running" | "needs_review" | "complete" | "failed";

export type EvidenceItem = {
  source: string;
  quote: string;
  relevance: string;
};

export type InterviewAnswer = {
  question: string;
  answer: string;
  guardrailNotes: string[];
  evidence: EvidenceItem[];
};

export type AnalysisResponse = {
  sessionId: string;
  status: AnalysisStatus;
  message: string;
  answers: InterviewAnswer[];
};
