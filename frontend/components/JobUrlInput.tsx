import { Link } from "lucide-react";

export default function JobUrlInput() {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-md bg-muted">
          <Link className="size-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Job URL</h2>
          <p className="text-sm text-muted-foreground">TODO: Scrape and normalize the job description.</p>
        </div>
      </div>
      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <input
          className="min-h-11 flex-1 rounded-md border border-border bg-white px-3 text-sm outline-none ring-primary/25 transition focus:ring-4"
          placeholder="https://company.com/careers/software-engineer"
          type="url"
        />
        <button className="min-h-11 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition hover:opacity-90">
          Analyze
        </button>
      </div>
    </section>
  );
}
