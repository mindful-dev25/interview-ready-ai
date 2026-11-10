import { useMemo, useState } from "react";
import { fetchFinalReport, requestRevision, reviewAnswer, startAnalysis } from "@/lib/api";
import { collectEvidence, countReviews, errorMessage, isReviewed } from "@/lib/answers";
import type { AnalysisStatus, InterviewAnswer, ReviewAction } from "@/lib/types";

/** Session state and API actions for analysis, answer review, revision, and the final report. */
export function useInterviewSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("queued");
  const [answers, setAnswers] = useState<InterviewAnswer[]>([]);
  const [loading, setLoading] = useState(false);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const [revisingAnswerId, setRevisingAnswerId] = useState<string | null>(null);
  const [revisionNotes, setRevisionNotes] = useState("");
  const [revisionLoading, setRevisionLoading] = useState(false);

  const [reportLoading, setReportLoading] = useState(false);
  const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const evidenceItems = useMemo(() => collectEvidence(answers), [answers]);
  const reviewCounts = useMemo(() => countReviews(answers), [answers]);
  const reportReady = answers.length > 0 && answers.every(isReviewed);

  function replaceAnswer(updated: InterviewAnswer) {
    setAnswers((current) => current.map((answer) => (answer.id === updated.id ? updated : answer)));
  }

  async function analyze(jobUrl: string, resumeText: string) {
    if (!jobUrl.trim()) return;

    setLoading(true);
    setAnalysisStatus("running");
    setReportMarkdown(null);
    setReportError(null);
    setReviewError(null);
    setWarnings([]);

    try {
      const response = await startAnalysis(jobUrl.trim(), resumeText.trim() || undefined);
      setSessionId(response.session_id);
      setAnalysisStatus(response.status);
      setAnswers(response.answers ?? []);
      setWarnings(response.metadata?.warnings ?? []);
    } catch (error: unknown) {
      setAnalysisStatus("failed");
      setReviewError(errorMessage(error, "Failed to start analysis."));
    } finally {
      setLoading(false);
    }
  }

  async function review(answerId: string, action: ReviewAction, editedAnswer?: string) {
    if (!sessionId) {
      setReviewError("Session is not available for review actions.");
      return;
    }

    setReviewError(null);
    try {
      const result = await reviewAnswer(sessionId, answerId, action, editedAnswer);
      if (result.answer) {
        replaceAnswer(result.answer);
      }
      if (result.session_status) {
        setAnalysisStatus(result.session_status);
      }
    } catch (error: unknown) {
      setReviewError(errorMessage(error, "Unable to update review status."));
    }
  }

  function toggleRevision(answerId: string) {
    setRevisingAnswerId((current) => (current === answerId ? null : answerId));
    setRevisionNotes("");
    setReviewError(null);
  }

  async function submitRevision(answerId: string) {
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
      replaceAnswer(result.answer);
      if (result.session_status) {
        setAnalysisStatus(result.session_status);
      }
    } catch (error: unknown) {
      setReviewError(errorMessage(error, "Revision failed."));
    } finally {
      setRevisionLoading(false);
      setRevisingAnswerId(null);
      setRevisionNotes("");
    }
  }

  async function generateReport() {
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
    } catch (error: unknown) {
      setReportError(errorMessage(error, "Failed to load the final report."));
    } finally {
      setReportLoading(false);
    }
  }

  return {
    analysisStatus,
    answers,
    loading,
    warnings,
    reviewError,
    evidenceItems,
    reviewCounts,
    revision: { answerId: revisingAnswerId, notes: revisionNotes, setNotes: setRevisionNotes, loading: revisionLoading },
    report: { ready: reportReady, loading: reportLoading, markdown: reportMarkdown, error: reportError },
    analyze,
    review,
    toggleRevision,
    submitRevision,
    generateReport,
  };
}
