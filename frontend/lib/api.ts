import type { AnalysisResponse, FinalReportResponse, ReviewResponse, RevisionResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

function normalizeUrl(url: string): string {
  if (!/^https?:\/\//i.test(url)) {
    return `https://${url}`;
  }
  return url;
}

export async function startAnalysis(jobUrl: string, resumeText?: string): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/analysis`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ job_url: normalizeUrl(jobUrl), resume_text: resumeText }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Failed to start interview analysis.");
  }

  const data = await response.json();
  return {
    sessionId: data.session_id,
    status: data.status,
    message: data.message,
    questions: data.questions,
    answers: data.answers ?? [],
    next_action: data.next_action,
  };
}

export async function reviewAnswer(
  sessionId: string,
  answerId: string,
  action: "approve" | "edit" | "request_revision",
  editedAnswer?: string,
): Promise<ReviewResponse> {
  const response = await fetch(`${API_BASE_URL}/review`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
      answer_id: answerId,
      action,
      edited_answer: editedAnswer,
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Failed to submit review action.");
  }

  return response.json();
}

export async function requestRevision(
  sessionId: string,
  answerId: string,
  reviewerNotes: string,
): Promise<RevisionResponse> {
  const response = await fetch(`${API_BASE_URL}/revision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      answer_id: answerId,
      reviewer_notes: reviewerNotes,
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Failed to request revision.");
  }
  return response.json();
}

export async function fetchFinalReport(sessionId: string): Promise<FinalReportResponse> {
  const response = await fetch(`${API_BASE_URL}/report/${sessionId}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? "Failed to fetch final report.");
  }

  return response.json();
}
