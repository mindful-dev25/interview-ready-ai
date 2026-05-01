import { FileText } from "lucide-react";

export default function FinalReport() {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-md bg-muted">
          <FileText className="size-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Final Report</h2>
          <p className="text-sm text-muted-foreground">TODO: Render approved answers, evidence, and coaching notes.</p>
        </div>
      </div>
      <div className="mt-5 rounded-md border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
        Final report preview will appear here after human review.
      </div>
    </section>
  );
}
