import type {
  AnalysisResponse,
  FinalReportResponse,
  ResumeTextResponse,
  ReviewAction,
  ReviewResponse,
  RevisionResponse,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

/**
 * Call the API and return the parsed JSON. Passing a body makes it a POST:
 * FormData is sent as a file upload, anything else as JSON.
 * On an error response, throws with the server's `detail` message when it is a
 * string (validation errors send a list instead), otherwise with `fallbackError`.
 */
async function request<T>(path: string, fallbackError: string, body?: unknown): Promise<T> {
  const init: RequestInit | undefined =
    body === undefined
      ? undefined
      : body instanceof FormData
        ? { method: "POST", body }
        : {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          };

  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" && detail ? detail : fallbackError);
  }
  return response.json();
}

export function extractResumeText(file: File): Promise<ResumeTextResponse> {
  const form = new FormData();
  form.append("file", file);
  return request("/resume/extract", "Failed to read the PDF resume.", form);
}

export function startAnalysis(jobUrl: string, resumeText?: string): Promise<AnalysisResponse> {
  return request("/analysis", "Failed to start interview analysis.", {
    job_url: jobUrl,
    resume_text: resumeText,
  });
}

export function reviewAnswer(
  sessionId: string,
  answerId: string,
  action: ReviewAction,
  editedAnswer?: string,
): Promise<ReviewResponse> {
  return request("/review", "Failed to submit review action.", {
    session_id: sessionId,
    answer_id: answerId,
    action,
    edited_answer: editedAnswer,
  });
}

export function requestRevision(
  sessionId: string,
  answerId: string,
  reviewerNotes: string,
): Promise<RevisionResponse> {
  return request("/revision", "Failed to request revision.", {
    session_id: sessionId,
    answer_id: answerId,
    reviewer_notes: reviewerNotes,
  });
}

export function fetchFinalReport(sessionId: string): Promise<FinalReportResponse> {
  return request(`/report/${encodeURIComponent(sessionId)}`, "Failed to fetch final report.");
}
