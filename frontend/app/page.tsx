'use client';

import { useMemo, useState } from "react";
import AnalysisProgress from "@/components/AnalysisProgress";
import EvidencePanel from "@/components/EvidencePanel";
import FinalReport from "@/components/FinalReport";
import GuardrailBadge from "@/components/GuardrailBadge";
import HumanReviewControls from "@/components/HumanReviewControls";
import InterviewQuestionCard from "@/components/InterviewQuestionCard";
import JobUrlInput from "@/components/JobUrlInput";
import ResumeUpload from "@/components/ResumeUpload";
import { reviewAnswer, requestRevision, startAnalysis, fetchFinalReport } from "@/lib/api";
import type { AnalysisStatus, EvidenceItem, InterviewAnswer } from "@/lib/types";

const badgeTone: Record<string, "neutral" | "success" | "warning"> = {
  pending: "warning",
  needs_revision: "warning",
  approved: "success",
  edited: "success",
};

export default function Home() {
  const [jobUrl, setJobUrl] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [resumeFileName, setResumeFileName] = useState<string | undefined>(undefined);
  const [fileError, setFileError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("queued");
  const [message, setMessage] = useState<string>("Enter a job URL and resume text to start the workflow.");
  const [answers, setAnswers] = useState<InterviewAnswer[]>([]);
  const [selectedAnswerId, setSelectedAnswerId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [revisingAnswerId, setRevisingAnswerId] = useState<string | null>(null);
  const [revisionNotes, setRevisionNotes] = useState("");
  const [revisionLoading, setRevisionLoading] = useState(false);

  const selectedAnswer = useMemo(
    () => answers.find((answer) => answer.id === selectedAnswerId) ?? answers[0] ?? null,
    [answers, selectedAnswerId],
  );

  const evidenceItems = useMemo(() => {
    const seen = new Set<string>();
    const items: EvidenceItem[] = [];
    answers.forEach((answer) => {
      answer.evidence_used?.forEach((item) => {
        const key = `${item.id ?? item.quote}-${item.source ?? item.source_type}`;
        if (!seen.has(key)) {
          seen.add(key);
          items.push({
            id: item.id,
            source: item.source ?? item.source_type ?? "Evidence",
            quote: item.quote,
            relevance: item.relevance ?? "",
          });
        }
      });
    });
    return items;
  }, [answers]);

  const reportReady = answers.length > 0 && answers.every((answer) => answer.human_status === "approved" || answer.human_status === "edited");

  const reviewCounts = useMemo(() => {
    const counts = { pending: 0, approved: 0, edited: 0, needs_revision: 0 };
    answers.forEach((answer) => {
      const status = answer.human_status ?? "pending";
      counts[status as keyof typeof counts] += 1;
    });
    return counts;
  }, [answers]);

  async function onAnalyze() {
    if (!jobUrl.trim()) {
      setMessage("Please enter a job URL before starting analysis.");
      return;
    }

    setLoading(true);
    setReportMarkdown(null);
    setReportError(null);
    setReviewError(null);
    setMessage("Generating draft answers from the provided job URL and resume context...");

    try {
      const response = await startAnalysis(jobUrl.trim(), resumeText.trim() || undefined);
      setSessionId(response.sessionId);
      setAnalysisStatus(response.status);
      setMessage(response.message || "Draft answers are ready.");
      setAnswers(response.answers ?? []);
      setSelectedAnswerId(response.answers?.[0]?.id ?? null);
    } catch (error: unknown) {
      setMessage("Failed to start the workflow. Please check your inputs and try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleReviewAction(answerId: string, action: "approve" | "edit" | "request_revision", editedAnswer?: string) {
    if (!sessionId) {
      setReviewError("Session is not available for review actions.");
      return;
    }

    setReviewError(null);
    try {
      const result = await reviewAnswer(sessionId, answerId, action, editedAnswer);
      if (result.answer) {
        setAnswers((current) => current.map((answer) => (answer.id === result.answer?.id ? result.answer : answer)));
        setSelectedAnswerId(result.answer.id);
      }
      setAnalysisStatus((prev) => (reviewCounts.pending - 1 <= 0 ? "complete" : prev));
    } catch (error: unknown) {
      setReviewError(error instanceof Error ? error.message : "Unable to update review status.");
    }
  }

  async function handleRevisionSubmit(answerId: string) {
    if (!sessionId) {
      setReviewError("Session is not available for revision.");
      return;
    }
    if (!revisionNotes.trim()) {
      setReviewError("Please enter revision notes before submitting.");
      return;
    }

    setRevisionLoading(true);
    setReviewError(null);
    try {
      const result = await requestRevision(sessionId, answerId, revisionNotes);
      setAnswers((current) => current.map((a) => (a.id === result.answer.id ? result.answer : a)));
      setSelectedAnswerId(result.answer.id);
    } catch (error: unknown) {
      setReviewError(error instanceof Error ? error.message : "Revision failed.");
    } finally {
      setRevisionLoading(false);
      setRevisingAnswerId(null);
      setRevisionNotes("");
    }
  }

  async function onGenerateReport() {
    if (!sessionId) {
      setReportError("A completed session is required to generate the final report.");
      return;
    }

    setReportLoading(true);
    setReportError(null);

    try {
      const report = await fetchFinalReport(sessionId);
      setReportMarkdown(report.report_markdown);
      setAnalysisStatus(report.status);
      setMessage(report.message);
    } catch (error: unknown) {
      setReportError(error instanceof Error ? error.message : "Failed to load the final report.");
    } finally {
      setReportLoading(false);
    }
  }

  function handleFileChange(file: File | null) {
    setFileError(null);
    setResumeFileName(file?.name);
    if (!file) {
      return;
    }

    const allowed = ["text/plain", "text/markdown"];
    if (!allowed.includes(file.type) && !file.name.match(/\.(txt|md)$/i)) {
      setFileError("Only plain text or markdown resume files are supported in the MVP.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : "";
      setResumeText(text);
    };
    reader.onerror = () => {
      setFileError("Unable to read the uploaded file.");
    };
    reader.readAsText(file);
  }

  function renderAnswerText(answer: InterviewAnswer) {
    return answer.final_answer?.trim() ? answer.final_answer : answer.draft_answer;
  }

  return (
    <main className="min-h-screen px-6 py-8 md:px-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="flex flex-col gap-3">
          <h1 className="max-w-3xl text-3xl font-semibold tracking-normal text-foreground md:text-4xl">
            Interview Ready AI
          </h1>
        </header>

        <section className="grid gap-4 md:grid-cols-[1fr_1fr]">
          <ResumeUpload
            resumeText={resumeText}
            fileName={resumeFileName}
            onTextChange={setResumeText}
            onFileChange={handleFileChange}
            fileError={fileError}
          />
          <JobUrlInput jobUrl={jobUrl} onJobUrlChange={setJobUrl} onSubmit={onAnalyze} isLoading={loading} />
        </section>

        <AnalysisProgress status={analysisStatus} />

        <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            {answers.length === 0 ? (
              <div className="rounded-lg border border-border bg-white p-5 shadow-sm">
                <p className="text-sm text-muted-foreground">No answer drafts yet. Start analysis to generate questions and answer drafts.</p>
              </div>
            ) : (
              answers.map((answer) => (
                <InterviewQuestionCard
                  key={answer.id}
                  question={answer.question.question}
                  answer={renderAnswerText(answer)}
                >
                  <div className="flex flex-col items-end gap-2 w-full">
                    <GuardrailBadge
                      label={
                        answer.human_status === "approved"
                          ? "Approved"
                          : answer.human_status === "edited"
                          ? "Edited"
                          : answer.human_status === "needs_revision"
                          ? "Needs revision"
                          : "Needs review"
                      }
                      tone={badgeTone[answer.human_status ?? "pending"]}
                    />
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleReviewAction(answer.id, "approve")}
                        className="rounded-md border border-border bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setRevisingAnswerId(revisingAnswerId === answer.id ? null : answer.id);
                          setRevisionNotes("");
                          setReviewError(null);
                        }}
                        className="rounded-md border border-border bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800"
                      >
                        {revisingAnswerId === answer.id ? "Cancel" : "Request revision"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const edited = prompt("Edit final answer:", renderAnswerText(answer));
                          if (edited !== null) {
                            handleReviewAction(answer.id, "edit", edited);
                          }
                        }}
                        className="rounded-md border border-border bg-slate-50 px-3 py-2 text-sm font-medium text-foreground"
                      >
                        Edit
                      </button>
                    </div>
                    {revisingAnswerId === answer.id && (
                      <div className="mt-2 w-full">
                        <textarea
                          className="w-full rounded-md border border-border bg-background p-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
                          rows={3}
                          placeholder="Describe what needs to change (e.g. 'Add a specific metric', 'Make it more concise')..."
                          value={revisionNotes}
                          onChange={(e) => setRevisionNotes(e.target.value)}
                        />
                        {reviewError && revisingAnswerId === answer.id && (
                          <p className="mt-1 text-sm text-red-700">{reviewError}</p>
                        )}
                        <button
                          type="button"
                          disabled={revisionLoading}
                          onClick={() => handleRevisionSubmit(answer.id)}
                          className="mt-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {revisionLoading ? "Revising..." : "Submit revision"}
                        </button>
                      </div>
                    )}
                  </div>
                </InterviewQuestionCard>
              ))
            )}
          </div>

          <aside className="space-y-4">
            <EvidencePanel items={evidenceItems} />
            <HumanReviewControls
              pendingCount={reviewCounts.pending}
              approvedCount={reviewCounts.approved}
              editedCount={reviewCounts.edited}
              needsRevisionCount={reviewCounts.needs_revision}
              onGenerateReport={onGenerateReport}
              reportReady={reportReady}
              reportLoading={reportLoading}
            />
            <FinalReport markdown={reportMarkdown ?? undefined} isLoading={reportLoading} ready={reportReady && Boolean(reportMarkdown)} error={reportError} />
          </aside>
        </section>

        {reviewError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{reviewError}</div>
        ) : null}
        <div className="rounded-lg border border-border bg-white p-5 text-sm text-muted-foreground">
          {message}
        </div>
      </div>
    </main>
  );
}
