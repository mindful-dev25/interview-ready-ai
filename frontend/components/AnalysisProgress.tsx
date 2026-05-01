type AnalysisProgressProps = {
  status: string;
};

const steps = ["Resume", "Job", "Research", "Draft", "Review", "Report"];

export default function AnalysisProgress({ status }: AnalysisProgressProps) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold">Analysis Progress</h2>
        <span className="text-sm font-medium text-primary">{status}</span>
      </div>
      <div className="mt-5 grid gap-2 sm:grid-cols-6">
        {steps.map((step) => (
          <div key={step} className="rounded-md border border-border bg-muted/40 px-3 py-2 text-center text-sm">
            {step}
          </div>
        ))}
      </div>
    </section>
  );
}
