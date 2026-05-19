import { FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";

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
          <p className="text-sm text-muted-foreground">
            Preview the generated final report after all answers are reviewed.
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-md border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
        {isLoading ? (
          "Generating report..."
        ) : error ? (
          <span className="text-red-700">{error}</span>
        ) : ready && markdown ? (
          <div className="prose prose-sm max-w-none text-foreground
            [&_h1]:text-xl [&_h1]:font-bold [&_h1]:mb-3 [&_h1]:mt-4 [&_h1]:text-foreground
            [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mb-2 [&_h2]:mt-4 [&_h2]:text-foreground
            [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mb-1 [&_h3]:mt-3 [&_h3]:text-foreground
            [&_p]:mb-2 [&_p]:leading-6
            [&_ul]:mb-2 [&_ul]:ml-4 [&_ul]:list-disc
            [&_ol]:mb-2 [&_ol]:ml-4 [&_ol]:list-decimal
            [&_li]:mb-1 [&_li]:leading-6
            [&_strong]:font-semibold [&_strong]:text-foreground
            [&_hr]:my-4 [&_hr]:border-border">
            <ReactMarkdown>{markdown}</ReactMarkdown>
          </div>
        ) : (
          "Final report will appear here once all answers are approved or edited."
        )}
      </div>
    </section>
  );
}
