import type { AnalysisResponse } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export async function startAnalysis(jobUrl: string, resumeText?: string): Promise<AnalysisResponse> {
  // TODO: Call the FastAPI backend once the workflow contract is finalized.
  const response = await fetch(`${API_BASE_URL}/analysis`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ job_url: jobUrl, resume_text: resumeText }),
  });

  if (!response.ok) {
    throw new Error("Failed to start interview analysis.");
  }

  const data = await response.json();
  return {
    sessionId: data.session_id,
    status: data.status,
    message: data.message,
    answers: data.answers ?? [],
  };
}
