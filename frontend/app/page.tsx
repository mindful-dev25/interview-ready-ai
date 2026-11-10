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

        <section className="grid gap-4 md:grid-cols-[1fr_1fr]">
          <ResumeUpload
            resumeText={resume.resumeText}
            fileName={resume.resumeFileName}
            onTextChange={resume.setResumeText}
            onFileChange={resume.handleFileChange}
            fileError={resume.fileError}
            isReadingFile={resume.isReadingFile}
          />
          <JobUrlInput
            jobUrl={jobUrl}
            onJobUrlChange={setJobUrl}
            onSubmit={() => session.analyze(jobUrl, resume.resumeText)}
            isLoading={session.loading}
            disabled={resume.isReadingFile}
          />
        </section>

        <AnalysisProgress status={session.analysisStatus} />

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
              session.answers.map((answer) => (
                <AnswerReviewCard
                  key={answer.id}
                  answer={answer}
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

          <aside className="space-y-4">
            <HumanReviewControls
              pendingCount={reviewCounts.pending}
              approvedCount={reviewCounts.approved}
              editedCount={reviewCounts.edited}
              needsRevisionCount={reviewCounts.needs_revision}
              onGenerateReport={session.generateReport}
              reportReady={report.ready}
              reportLoading={report.loading}
            />
            <FinalReport
              markdown={report.markdown ?? undefined}
              isLoading={report.loading}
              ready={report.ready && Boolean(report.markdown)}
              error={report.error}
            />
            <EvidencePanel items={session.evidenceItems} />
          </aside>
        </section>

        {session.reviewError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{session.reviewError}</div>
        ) : null}
      </div>
    </main>
  );
}
