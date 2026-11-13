import type { AnalysisPhase, AnalysisProgressUpdate, AnalysisStatus } from "@/lib/types";

type AnalysisProgressProps = {
  status: AnalysisStatus;
  /** Live progress reported by the backend; only present while an analysis is running. */
  progress?: AnalysisProgressUpdate | null;
};

const steps = ["Resume", "Job", "Research", "Draft", "Review", "Report"];

const activeStepIndex: Record<AnalysisStatus, number> = {
  queued: -1,
  running: 3,
  needs_review: 4,
  complete: 5,
  failed: -1,
};

const phaseStepIndex: Record<AnalysisPhase, number> = { resume: 0, job: 1, research: 2, draft: 3 };

const statusLabel: Record<AnalysisStatus, string> = {
  queued: "Waiting",
  running: "Generating drafts...",
  needs_review: "Needs review",
  complete: "Complete",
  failed: "Failed",
};

const statusColor: Record<AnalysisStatus, string> = {
  queued: "text-muted-foreground",
  running: "text-amber-600",
  needs_review: "text-amber-600",
  complete: "text-emerald-600",
  failed: "text-red-600",
};

export default function AnalysisProgress({ status, progress }: AnalysisProgressProps) {
  const live = status === "running" ? (progress ?? null) : null;
  const current = live ? phaseStepIndex[live.phase] : activeStepIndex[status];

  return (
    <div className="px-1 py-2">
      <div className="flex items-center gap-3">
        {steps.map((step, index) => {
          const isDone = index < current;
          const isActive = index === current;

          return (
            <div key={step} className="flex flex-1 items-center gap-2">
              <div className="flex flex-1 flex-col items-center gap-1.5">
                <div
                  className={[
                    "flex size-7 items-center justify-center rounded-full text-xs font-semibold transition-all",
                    isDone
                      ? "bg-emerald-500 text-white"
                      : isActive
                      ? "bg-primary text-primary-foreground ring-4 ring-primary/20"
                      : "bg-muted text-muted-foreground",
                  ].join(" ")}
                >
                  {isDone ? "✓" : index + 1}
                </div>
                <span
                  className={[
                    "text-xs font-medium",
                    isDone
                      ? "text-emerald-600"
                      : isActive
                      ? "text-primary"
                      : "text-muted-foreground",
                  ].join(" ")}
                >
                  {step}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={[
                    "mb-4 h-px flex-1 transition-colors",
                    isDone ? "bg-emerald-400" : "bg-border",
                  ].join(" ")}
                />
              )}
            </div>
          );
        })}
        <span className={["ml-2 shrink-0 text-sm font-medium tabular-nums", statusColor[status]].join(" ")}>
          {live ? `Analyzing... ${live.percent}%` : statusLabel[status]}
        </span>
      </div>

      {live && (
        <div className="mt-3">
          <div
            className="h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label="Analysis progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={live.percent}
            aria-valuetext={`${live.percent}%: ${live.message}`}
          >
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
              style={{ width: `${live.percent}%` }}
            />
          </div>
          <p className="mt-1.5 text-sm text-muted-foreground">{live.message}</p>
        </div>
      )}
    </div>
  );
}
