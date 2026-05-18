import type { AnalysisStatus } from "@/lib/types";

type AnalysisProgressProps = {
  status: AnalysisStatus;
};

const steps = ["Resume", "Job", "Research", "Draft", "Review", "Report"];

const activeStepIndex: Record<AnalysisStatus, number> = {
  queued: -1,
  running: 3,
  needs_review: 4,
  complete: 5,
  failed: -1,
};

const statusLabel: Record<AnalysisStatus, string> = {
  queued: "Waiting",
  running: "Generating drafts...",
  needs_review: "Needs review",
  complete: "Complete",
  failed: "Failed",
};

export default function AnalysisProgress({ status }: AnalysisProgressProps) {
  const current = activeStepIndex[status];

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold">Analysis Progress</h2>
        <span className="text-sm font-medium text-primary">{statusLabel[status]}</span>
      </div>
      <div className="mt-5 grid gap-2 sm:grid-cols-6">
        {steps.map((step, index) => {
          const isDone = index < current;
          const isActive = index === current;
          return (
            <div
              key={step}
              className={[
                "rounded-md border px-3 py-2 text-center text-sm font-medium transition-colors",
                isDone
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                  : isActive
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-muted/40 text-muted-foreground",
              ].join(" ")}
            >
              {isDone ? `✓ ${step}` : step}
            </div>
          );
        })}
      </div>
    </section>
  );
}
