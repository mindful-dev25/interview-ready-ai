'use client';

import { useState } from "react";
import AnalysisProgress from "@/components/AnalysisProgress";
import AnswerReviewCard from "@/components/AnswerReviewCard";
import EvidencePanel from "@/components/EvidencePanel";
import FinalReport from "@/components/FinalReport";
import HumanReviewControls from "@/components/HumanReviewControls";
import JobUrlInput from "@/components/JobUrlInput";
import ResumeUpload from "@/components/ResumeUpload";
import { useInterviewSession } from "@/lib/hooks/useInterviewSession";
import { useResumeInput } from "@/lib/hooks/useResumeInput";

export default function Home() {
  const [jobUrl, setJobUrl] = useState("");
  const [jobText, setJobText] = useState("");
  const resume = useResumeInput();
  const session = useInterviewSession();
  const { revision, report, reviewCounts } = session;

  return (
    <main className="min-h-screen px-6 py-8 md:px-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="flex flex-col gap-3">
          <h1 className="max-w-3xl text-3xl font-semibold tracking-normal text-foreground md:text-4xl">
            Interview Ready AI
          </h1>
        </header>

        <section className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <ResumeUpload
              resumeText={resume.resumeText}
              fileName={resume.resumeFileName}
              onTextChange={resume.setResumeText}
              onFileChange={resume.handleFileChange}
              fileError={resume.fileError}
              isReadingFile={resume.isReadingFile}
            />
            <JobUrlInput jobUrl={jobUrl} onJobUrlChange={setJobUrl} jobText={jobText} onJobTextChange={setJobText} />
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={() => session.analyze(jobUrl, resume.resumeText, jobText)}
              // Also blocked while a resume file is still being read, so it is not left out of the analysis.
              disabled={session.loading || resume.isReadingFile}
              className="min-h-11 w-full rounded-md bg-primary px-8 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
            >
              {session.loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>
        </section>

        <AnalysisProgress status={session.analysisStatus} progress={session.progress} />

        {session.analysisError && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {session.analysisError}
          </div>
        )}

        {session.warnings.length > 0 && (
          <div role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <ul className="list-disc space-y-1 pl-5">
              {session.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        )}

        <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            {session.answers.length === 0 ? (
              <div className="rounded-lg border border-border bg-white p-5 shadow-sm">
                <p className="text-sm text-muted-foreground">No answer drafts yet. Start analysis to generate questions and answer drafts.</p>
              </div>
            ) : (
              session.answers.map((answer, index) => (
                <AnswerReviewCard
                  key={answer.id}
                  answer={answer}
                  number={index + 1}
                  evidence={session.evidenceIndex}
                  isRevising={revision.answerId === answer.id}
                  revisionNotes={revision.notes}
                  revisionLoading={revision.loading}
                  reviewError={session.reviewError}
                  onApprove={() => session.review(answer.id, "approve")}
                  onEdit={(edited) => session.review(answer.id, "edit", edited)}
                  onToggleRevision={() => session.toggleRevision(answer.id)}
                  onRevisionNotesChange={revision.setNotes}
                  onSubmitRevision={() => session.submitRevision(answer.id)}
                />
              ))
            )}
          </div>

          {/* Sticky on wide screens: the answers column is much taller, so the summary and evidence follow the reader. */}
          <aside className="flex flex-col gap-4 lg:sticky lg:top-6 lg:max-h-[calc(100vh-3rem)] lg:self-start">
            <HumanReviewControls
              pendingCount={reviewCounts.pending}
              approvedCount={reviewCounts.approved}
              editedCount={reviewCounts.edited}
              needsRevisionCount={reviewCounts.needs_revision}
              onGenerateReport={session.generateReport}
              reportReady={report.ready}
              reportLoading={report.loading}
              onApproveAll={session.approveAll}
              approvingAll={session.approvingAll}
            />
            <EvidencePanel items={session.evidenceItems} />
          </aside>
        </section>

        {/* Full width under the answers: in the side column a long report made that column far taller than the answers. */}
        <FinalReport
          // Hidden again if an answer is reopened after the report was made.
          markdown={report.ready ? report.markdown ?? undefined : undefined}
          isLoading={report.loading}
          error={report.error}
        />

        {session.reviewError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{session.reviewError}</div>
        ) : null}
      </div>
    </main>
  );
}
