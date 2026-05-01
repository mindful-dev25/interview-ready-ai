import { Upload } from "lucide-react";

export default function ResumeUpload() {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-md bg-muted">
          <Upload className="size-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Resume</h2>
          <p className="text-sm text-muted-foreground">TODO: Add PDF, DOCX, and text upload handling.</p>
        </div>
      </div>
      <label className="mt-5 flex min-h-36 cursor-pointer items-center justify-center rounded-md border border-dashed border-border bg-muted/40 px-4 text-center text-sm text-muted-foreground">
        <input className="sr-only" type="file" accept=".pdf,.doc,.docx,.txt" />
        Select a resume file
      </label>
    </section>
  );
}
