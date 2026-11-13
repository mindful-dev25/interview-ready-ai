import { Upload } from "lucide-react";

type ResumeUploadProps = {
  resumeText: string;
  fileName?: string;
  onTextChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
  fileError?: string | null;
  isReadingFile?: boolean;
};

export default function ResumeUpload({
  resumeText,
  fileName,
  onTextChange,
  onFileChange,
  fileError,
  isReadingFile = false,
}: ResumeUploadProps) {
  return (
    <section className="flex flex-col rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted">
          <Upload className="size-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Resume</h2>
          <p className="text-sm text-muted-foreground">
            Upload your resume or paste its text, so the answers are grounded in your experience.
          </p>
        </div>
      </div>

      <div className="mt-4 flex min-h-11 items-center gap-3">
        <label className="inline-flex min-h-11 shrink-0 cursor-pointer items-center justify-center rounded-md border border-dashed border-border bg-muted/40 px-4 text-sm font-medium text-muted-foreground transition hover:border-primary">
          <input
            className="sr-only"
            type="file"
            accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
            onChange={(event) => {
              onFileChange(event.target.files?.[0] ?? null);
              // Clear the input so choosing the same file again triggers another read.
              event.target.value = "";
            }}
          />
          Upload resume (PDF or text)
        </label>
        {fileName ? (
          <span className="min-w-0 truncate text-sm text-muted-foreground" role="status">
            {isReadingFile ? `Reading ${fileName}...` : fileName}
          </span>
        ) : null}
      </div>

      <label className="mt-4 block text-sm font-medium" htmlFor="resume-text">
        Or paste the resume text
      </label>
      <p className="text-sm text-muted-foreground">
        Text from an uploaded file appears here for you to check and edit.
      </p>
      <textarea
        id="resume-text"
        className="mt-2 min-h-[9rem] w-full flex-1 rounded-md border border-border bg-white px-3 py-3 text-sm outline-none ring-primary/25 transition focus:ring-4"
        placeholder="Paste your resume text here..."
        value={resumeText}
        onChange={(event) => onTextChange(event.target.value)}
      />

      {fileError ? <p className="mt-2 text-sm text-red-700">{fileError}</p> : null}
    </section>
  );
}
