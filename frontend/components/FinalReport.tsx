import { FileText } from "lucide-react";

type FinalReportProps = {
  markdown?: string;
  isLoading: boolean;
  ready: boolean;
  error?: string | null;
};

export default function FinalReport({ markdown, isLoading, ready, error }: FinalReportProps) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-md bg-muted">
          <FileText className="size-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Final Report</h2>
          <p className="text-sm text-muted-foreground">Preview the generated final report after all answers are reviewed.</p>
        </div>
      </div>

      <div className="mt-5 rounded-md border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
        {isLoading
          ? "Generating report..."
          : error
          ? error
          : ready
          ? markdown || "No report content is available."
          : "Final report will appear here once all answers are approved or edited."}
      </div>
    </section>
  );
}
