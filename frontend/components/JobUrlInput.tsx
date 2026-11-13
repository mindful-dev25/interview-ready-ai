import { Link } from "lucide-react";

type JobUrlInputProps = {
  jobUrl: string;
  onJobUrlChange: (value: string) => void;
  jobText: string;
  onJobTextChange: (value: string) => void;
};

export default function JobUrlInput({ jobUrl, onJobUrlChange, jobText, onJobTextChange }: JobUrlInputProps) {
  return (
    <section className="flex flex-col rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted">
          <Link className="size-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Job posting</h2>
          <p className="text-sm text-muted-foreground">
            Paste the job posting URL or the job description, so the answers are tailored to the role.
          </p>
        </div>
      </div>

      <input
        className="mt-4 min-h-11 w-full rounded-md border border-border bg-white px-3 text-sm outline-none ring-primary/25 transition focus:ring-4"
        placeholder="https://company.com/careers/software-engineer"
        type="url"
        aria-label="Job posting URL"
        value={jobUrl}
        onChange={(event) => onJobUrlChange(event.target.value)}
      />

      <label className="mt-4 block text-sm font-medium" htmlFor="job-description">
        Or paste the job description
      </label>
      <p className="text-sm text-muted-foreground">
        Used instead of the URL, for sites that block automated access.
      </p>
      <textarea
        id="job-description"
        className="mt-2 min-h-[9rem] w-full flex-1 rounded-md border border-border bg-white px-3 py-3 text-sm outline-none ring-primary/25 transition focus:ring-4"
        placeholder="Paste the full job description here..."
        value={jobText}
        onChange={(event) => onJobTextChange(event.target.value)}
      />
    </section>
  );
}
