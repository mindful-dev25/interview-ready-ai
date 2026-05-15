import json
import re
from typing import Any

from app.core.llm import GroqLLMClient, LLMGenerationError, LLMMalformedResponseError

MIN_WORD_COUNT = 75
SECTION_INDICATORS = [
    r"\bsummary\b",
    r"\bexperience\b",
    r"\beducation\b",
    r"\bskills?\b",
    r"\bprojects?\b",
    r"\baccomplishments?\b",
    r"\bachievements?\b",
]


class ResumeParser:
    """Parse raw resume text into structured JSON using Groq."""

    def __init__(self, llm_client: GroqLLMClient | None = None) -> None:
        self.llm = llm_client or GroqLLMClient()

    async def parse_text(self, resume_text: str) -> dict[str, Any]:
        cleaned_text = str(resume_text or "").strip()
        if not cleaned_text:
            raise ValueError("Resume text must not be empty. Please provide the full resume content.")

        if len(cleaned_text.split()) < MIN_WORD_COUNT or not self._has_resume_structure(cleaned_text):
            raise ValueError(
                "Resume text appears too short or lacks clear sections. "
                "Please provide a more complete resume with summary, experience, skills, and education details."
            )

        prompt = self._build_prompt(cleaned_text)
        response = await self.llm.generate(prompt=prompt, system_prompt=self._system_prompt())

        try:
            parsed = json.loads(response)
        except ValueError as exc:
            raise LLMMalformedResponseError(
                "Groq returned invalid JSON while parsing resume text."
            ) from exc

        return self._normalize_parsed_resume(parsed)

    def _has_resume_structure(self, text: str) -> bool:
        normalized = text.lower()
        return sum(bool(re.search(pattern, normalized)) for pattern in SECTION_INDICATORS) >= 3

    def _build_prompt(self, resume_text: str) -> str:
        return (
            "Convert the following resume text into a JSON object with the fields: "
            "candidate_summary, skills, tools_technologies, projects, work_experience, "
            "measurable_achievements, education_certifications. "
            "Use arrays for lists and provide strings for text fields. "
            "Do not include any markdown or explanatory text, only valid JSON. "
            "If a section is missing, return an empty array or empty string, not null.\n\n"
            f"Resume text:\n{resume_text.strip()}"
        )

    def _system_prompt(self) -> str:
        return (
            "You are a resume parsing assistant. Extract structured resume data exactly as valid JSON. "
            "Do not add any extra commentary."
        )

    def _normalize_parsed_resume(self, parsed: Any) -> dict[str, Any]:
        if not isinstance(parsed, dict):
            raise LLMMalformedResponseError("Parsed resume output must be a JSON object.")

        return {
            "candidate_summary": self._coerce_text(parsed.get("candidate_summary")),
            "skills": self._coerce_list(parsed.get("skills")),
            "tools_technologies": self._coerce_list(parsed.get("tools_technologies")),
            "projects": self._coerce_list(parsed.get("projects")),
            "work_experience": self._coerce_list(parsed.get("work_experience")),
            "measurable_achievements": self._coerce_list(parsed.get("measurable_achievements")),
            "education_certifications": self._coerce_list(parsed.get("education_certifications")),
        }

    def _coerce_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return ""
        return str(value).strip()

    def _coerce_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]
