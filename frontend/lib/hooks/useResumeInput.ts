import { useRef, useState } from "react";
import { extractResumeText } from "@/lib/api";

const TEXT_TYPES = ["text/plain", "text/markdown"];
const TEXT_EXTENSIONS = /\.(txt|md)$/i;

function isPdf(file: File) {
  return file.type === "application/pdf" || /\.pdf$/i.test(file.name);
}

function isTextFile(file: File) {
  return TEXT_TYPES.includes(file.type) || TEXT_EXTENSIONS.test(file.name);
}

/** Resume text typed by the user or loaded from a PDF, plain-text or markdown file. */
export function useResumeInput() {
  const [resumeText, setResumeText] = useState("");
  const [resumeFileName, setResumeFileName] = useState<string | undefined>(undefined);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isReadingFile, setIsReadingFile] = useState(false);
  // Counts file selections, so a slow read of an earlier file cannot overwrite a later one.
  const latestSelection = useRef(0);

  async function handleFileChange(file: File | null) {
    const selection = ++latestSelection.current;
    const isLatest = () => selection === latestSelection.current;

    setFileError(null);
    setResumeFileName(file?.name);
    setIsReadingFile(false);
    if (!file) return;

    if (!isPdf(file) && !isTextFile(file)) {
      setResumeFileName(undefined);
      setFileError("Upload a PDF, plain text or markdown file.");
      return;
    }

    setIsReadingFile(true);
    try {
      // PDFs are converted to text by the backend; text files are read in the browser.
      const text = isPdf(file) ? (await extractResumeText(file)).text : await file.text();
      if (isLatest()) setResumeText(text);
    } catch (error) {
      if (isLatest()) {
        // Drop the name so a failed file is not shown as if it had been loaded.
        setResumeFileName(undefined);
        setFileError(error instanceof Error && error.message ? error.message : "Unable to read the uploaded file.");
      }
    } finally {
      if (isLatest()) setIsReadingFile(false);
    }
  }

  return { resumeText, setResumeText, resumeFileName, fileError, isReadingFile, handleFileChange };
}
