'use client';

type HumanReviewControlsProps = {
  pendingCount: number;
  approvedCount: number;
  editedCount: number;
  needsRevisionCount: number;
  onGenerateReport: () => void;
  reportReady: boolean;
  reportLoading: boolean;
  /** Approve every answer that is pending or needs revision. */
  onApproveAll: () => void;
  approvingAll: boolean;
};

export default function HumanReviewControls({
  pendingCount,
  approvedCount,
  editedCount,
  needsRevisionCount,
  onGenerateReport,
  reportReady,
  reportLoading,
  onApproveAll,
  approvingAll,
}: HumanReviewControlsProps) {
  const unreviewedCount = pendingCount + needsRevisionCount;
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Review summary</h2>
      <p className="text-sm text-muted-foreground">
        Approve or edit every answer, then generate the final report.
      </p>
      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        {pendingCount > 0 && (
          <span className="rounded-md border border-border bg-muted px-2 py-1">Pending: {pendingCount}</span>
        )}
        {approvedCount > 0 && (
          <span className="rounded-md border border-border bg-emerald-50 px-2 py-1 text-emerald-800">Approved: {approvedCount}</span>
        )}
        {editedCount > 0 && (
          <span className="rounded-md border border-border bg-slate-50 px-2 py-1">Edited: {editedCount}</span>
        )}
        {needsRevisionCount > 0 && (
          <span className="rounded-md border border-border bg-amber-50 px-2 py-1 text-amber-800">Needs revision: {needsRevisionCount}</span>
        )}
        {pendingCount === 0 && approvedCount === 0 && editedCount === 0 && needsRevisionCount === 0 && (
          <span className="text-muted-foreground">No answers yet.</span>
        )}
      </div>
      {unreviewedCount > 0 && (
        <button
          type="button"
          onClick={onApproveAll}
          disabled={approvingAll}
          className="mt-4 inline-flex min-h-11 w-full items-center justify-center whitespace-nowrap rounded-md border border-emerald-200 bg-emerald-50 px-4 text-sm font-medium text-emerald-800 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {approvingAll ? "Approving..." : `Approve all (${unreviewedCount})`}
        </button>
      )}
      {/* Full width under the text: beside it, the narrow side column squeezed the label onto three lines. */}
      <button
        type="button"
        onClick={onGenerateReport}
        disabled={!reportReady || reportLoading}
        className="mt-4 inline-flex min-h-11 w-full items-center justify-center whitespace-nowrap rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {reportLoading ? "Generating report..." : "Generate final report"}
      </button>
    </section>
  );
}
