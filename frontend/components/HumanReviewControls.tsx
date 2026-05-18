'use client';

type HumanReviewControlsProps = {
  pendingCount: number;
  approvedCount: number;
  editedCount: number;
  needsRevisionCount: number;
  onGenerateReport: () => void;
  reportReady: boolean;
  reportLoading: boolean;
};

export default function HumanReviewControls({
  pendingCount,
  approvedCount,
  editedCount,
  needsRevisionCount,
  onGenerateReport,
  reportReady,
  reportLoading,
}: HumanReviewControlsProps) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Review summary</h2>
          <p className="text-sm text-muted-foreground">
            Monitor answer review status and generate the final report once all approved or edited answers are ready.
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-sm">
            <span className="rounded-md border border-border bg-muted px-2 py-1">Pending: {pendingCount}</span>
            <span className="rounded-md border border-border bg-emerald-50 px-2 py-1">Approved: {approvedCount}</span>
            <span className="rounded-md border border-border bg-slate-50 px-2 py-1">Edited: {editedCount}</span>
            <span className="rounded-md border border-border bg-amber-50 px-2 py-1">Needs revision: {needsRevisionCount}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={onGenerateReport}
          disabled={!reportReady || reportLoading}
          className="inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {reportLoading ? "Generating report..." : "Generate final report"}
        </button>
      </div>
    </section>
  );
}
