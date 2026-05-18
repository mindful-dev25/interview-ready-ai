import { Upload } from "lucide-react";

type ResumeUploadProps = {
  resumeText: string;
  fileName?: string;
  onTextChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
  fileError?: string | null;
};

export default function ResumeUpload({ resumeText, fileName, onTextChange, onFileChange, fileError }: ResumeUploadProps) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-md bg-muted">
          <Upload className="size-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Resume</h2>
          <p className="text-sm text-muted-foreground">
            Paste resume text or upload a plain text file to ground the answer generation.
          </p>
        </div>
      </div>

      <textarea
        className="mt-5 min-h-[12rem] w-full rounded-md border border-border bg-white px-3 py-3 text-sm outline-none ring-primary/25 transition focus:ring-4"
        placeholder="Paste your resume text here..."
        value={resumeText}
        onChange={(event) => onTextChange(event.target.value)}
      />

      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
        <label className="inline-flex min-h-11 cursor-pointer items-center justify-center rounded-md border border-dashed border-border bg-muted/40 px-4 text-sm font-medium text-muted-foreground transition hover:border-primary">
          <input
            className="sr-only"
            type="file"
            accept=".txt,.md"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          />
          Upload plain text resume
        </label>
        {fileName ? <span className="text-sm text-muted-foreground">{fileName}</span> : null}
      </div>

      {fileError ? <p className="mt-2 text-sm text-red-700">{fileError}</p> : null}
    </section>
  );
}
