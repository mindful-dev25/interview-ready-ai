import type {
  AnalysisProgressUpdate,
  AnalysisResponse,
  AnalysisStreamEvent,
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
  if (!response.ok) throw await errorFrom(response, fallbackError);
  return response.json();
}

async function errorFrom(response: Response, fallbackError: string): Promise<Error> {
  const payload = await response.json().catch(() => null);
  const detail = payload?.detail;
  return new Error(typeof detail === "string" && detail ? detail : fallbackError);
}

export function extractResumeText(file: File): Promise<ResumeTextResponse> {
  const form = new FormData();
  form.append("file", file);
  return request("/resume/extract", "Failed to read the PDF resume.", form);
}

/**
 * Run an analysis, calling `onProgress` as the backend reports each step.
 * A pasted job description, when given, is used instead of fetching the URL.
 *
 * The response body is newline-delimited JSON: progress events, then one
 * result or error event.
 */
export async function startAnalysis(
  input: { jobUrl: string; resumeText?: string; jobText?: string },
  onProgress: (update: AnalysisProgressUpdate) => void,
): Promise<AnalysisResponse> {
  const fallbackError = "Failed to start interview analysis.";
  const response = await fetch(`${API_BASE_URL}/analysis/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_url: input.jobUrl, job_text: input.jobText, resume_text: input.resumeText }),
  });
  if (!response.ok || !response.body) throw await errorFrom(response, fallbackError);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffered = "";
  for (;;) {
    const { done, value } = await reader.read();
    buffered += decoder.decode(value, { stream: !done });

    // A network chunk can end mid-line, so only complete lines are parsed; the rest waits for more data.
    const lines = buffered.split("\n");
    buffered = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line) as AnalysisStreamEvent;
      if (event.type === "progress") onProgress(event);
      else if (event.type === "result") return event.data;
      else throw new Error(event.detail || fallbackError);
    }
    if (done) break;
  }
  throw new Error("The analysis stopped before a result arrived.");
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
