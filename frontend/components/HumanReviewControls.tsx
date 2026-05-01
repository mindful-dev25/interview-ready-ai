import { Check, MessageSquare, X } from "lucide-react";

export default function HumanReviewControls() {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Human Review</h2>
          <p className="text-sm text-muted-foreground">TODO: Capture reviewer edits, approvals, and revision requests.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium">
            <MessageSquare className="size-4" aria-hidden="true" />
            Comment
          </button>
          <button className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium">
            <X className="size-4" aria-hidden="true" />
            Revise
          </button>
          <button className="inline-flex min-h-10 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground">
            <Check className="size-4" aria-hidden="true" />
            Approve
          </button>
        </div>
      </div>
    </section>
  );
}
