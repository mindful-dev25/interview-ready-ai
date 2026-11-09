import { useState } from "react";

const ALLOWED_TYPES = ["text/plain", "text/markdown"];
const ALLOWED_EXTENSIONS = /\.(txt|md)$/i;

/** Resume text typed by the user or loaded from a plain-text/markdown file. */
export function useResumeInput() {
  const [resumeText, setResumeText] = useState("");
  const [resumeFileName, setResumeFileName] = useState<string | undefined>(undefined);
  const [fileError, setFileError] = useState<string | null>(null);

  function handleFileChange(file: File | null) {
    setFileError(null);
    setResumeFileName(file?.name);
    if (!file) return;

    if (!ALLOWED_TYPES.includes(file.type) && !ALLOWED_EXTENSIONS.test(file.name)) {
      setFileError("Only plain text or markdown resume files are supported in the MVP.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setResumeText(typeof reader.result === "string" ? reader.result : "");
    };
    reader.onerror = () => {
      setFileError("Unable to read the uploaded file.");
    };
    reader.readAsText(file);
  }

  return { resumeText, setResumeText, resumeFileName, fileError, handleFileChange };
}
