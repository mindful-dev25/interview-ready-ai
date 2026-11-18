'use client';

import { useEffect, useRef } from "react";
import { FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";

type FinalReportProps = {
  markdown?: string;
  isLoading: boolean;
  error?: string | null;
};

/**
 * The final report, shown full width under the answers once it is requested. It is
 * the session's end product, so it gets a readable width instead of a side column,
 * and it scrolls into view when it arrives.
 */
export default function FinalReport({ markdown, isLoading, error }: FinalReportProps) {
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (markdown) sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [markdown]);

  if (!isLoading && !error && !markdown) return null;

  return (
    <section ref={sectionRef} className="scroll-mt-6 rounded-lg border border-border bg-white p-5 shadow-sm md:p-8">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-md bg-muted">
          <FileText className="size-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Final Report</h2>
          <p className="text-sm text-muted-foreground">Built from the answers you approved or edited.</p>
        </div>
      </div>

      <div className="mt-6 text-sm text-muted-foreground">
        {isLoading ? (
          "Generating report..."
        ) : error ? (
          <span className="text-red-700">{error}</span>
        ) : (
          <div className="mx-auto max-w-3xl text-foreground
            [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mb-4 [&_h1]:mt-2
            [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:border-b [&_h2]:border-border [&_h2]:pb-2
            [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mb-2 [&_h3]:mt-5
            [&_p]:mb-3 [&_p]:text-[15px] [&_p]:leading-7
            [&_ul]:mb-3 [&_ul]:ml-5 [&_ul]:list-disc
            [&_ol]:mb-3 [&_ol]:ml-5 [&_ol]:list-decimal
            [&_li]:mb-1 [&_li]:text-[15px] [&_li]:leading-7
            [&_strong]:font-semibold
            [&_hr]:my-6 [&_hr]:border-border">
            <ReactMarkdown>{markdown}</ReactMarkdown>
          </div>
        )}
      </div>
    </section>
  );
}
