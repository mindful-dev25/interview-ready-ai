import re
from typing import Any

from app.core.llm import LLMClient
from app.core.llm_json import coerce_list, coerce_text, parse_json_response

MIN_WORD_COUNT = 75
MIN_SECTION_MATCHES = 3
SECTION_INDICATORS = [
    re.compile(pattern)
    for pattern in (
        r"\bsummary\b",
        r"\bexperience\b",
        r"\beducation\b",
        r"\bskills?\b",
        r"\bprojects?\b",
        r"\baccomplishments?\b",
        r"\bachievements?\b",
    )
]

_SYSTEM_PROMPT = (
    "You are a resume parsing assistant. Extract structured resume data exactly as valid JSON. "
    "Do not add any extra commentary."
)
_LIST_FIELDS = (
    "skills",
    "tools_technologies",
    "projects",
    "work_experience",
    "measurable_achievements",
    "education_certifications",
)


class ResumeParser:
    """Parse raw resume text into structured JSON using the LLM."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    async def parse_text(self, resume_text: str) -> dict[str, Any]:
        cleaned_text = str(resume_text or "").strip()
        if not cleaned_text:
            raise ValueError("Resume text must not be empty. Please provide the full resume content.")

        if len(cleaned_text.split()) < MIN_WORD_COUNT or not self._has_resume_structure(cleaned_text):
            raise ValueError(
                "Resume text appears too short or lacks clear sections. "
                "Please provide a more complete resume with summary, experience, skills, and education details."
            )

        response = await self.llm.generate(
            prompt=self._build_prompt(cleaned_text), system_prompt=_SYSTEM_PROMPT
        )
        parsed = parse_json_response(response, expect=dict, context="parsing resume text")

        return {
            "candidate_summary": coerce_text(parsed.get("candidate_summary")),
            **{field: coerce_list(parsed.get(field)) for field in _LIST_FIELDS},
        }

    def _has_resume_structure(self, text: str) -> bool:
        normalized = text.lower()
        matches = sum(bool(pattern.search(normalized)) for pattern in SECTION_INDICATORS)
        return matches >= MIN_SECTION_MATCHES

    def _build_prompt(self, resume_text: str) -> str:
        return (
            "Convert the following resume text into a JSON object with the fields: "
            "candidate_summary, skills, tools_technologies, projects, work_experience, "
            "measurable_achievements, education_certifications. "
            "Use arrays for lists and provide strings for text fields. "
            "Do not include any markdown or explanatory text, only valid JSON. "
            "If a section is missing, return an empty array or empty string, not null.\n\n"
            f"Resume text:\n{resume_text}"
        )
