import json
from typing import Any

from app.core.llm import GroqLLMClient, LLMGenerationError, LLMMalformedResponseError
from app.schemas import InterviewQuestion


class QuestionGenerator:
    """Generate tailored interview questions using Groq."""

    def __init__(self, llm_client: GroqLLMClient | None = None) -> None:
        self.llm = llm_client or GroqLLMClient()

    async def generate_questions(
        self,
        resume_data: dict[str, Any],
        job_requirements: dict[str, Any],
        company_research: dict[str, Any],
        skill_gaps: list[str] | None = None,
    ) -> list[InterviewQuestion]:
        prompt = self._build_prompt(resume_data, job_requirements, company_research, skill_gaps or [])
        response = await self.llm.generate(prompt=prompt, system_prompt=self._system_prompt())

        try:
            parsed = json.loads(response)
        except ValueError as exc:
            raise LLMMalformedResponseError(
                "Groq returned invalid JSON while generating questions."
            ) from exc

        return self._normalize_questions(parsed)

    def _build_prompt(
        self,
        resume_data: dict[str, Any],
        job_requirements: dict[str, Any],
        company_research: dict[str, Any],
        skill_gaps: list[str],
    ) -> str:
        return (
            "Generate exactly 7 tailored interview questions based on the provided resume, job requirements, "
            "company research, and skill gaps. "
            "Return only valid JSON as an array of objects, each with fields: id, question, category, "
            "difficulty, rationale, related_requirements. "
            "Categories: behavioral, technical, project_deep_dive, role_specific, company_motivation, weakness_gap_handling. "
            "Difficulty: easy, medium, hard. "
            "Each question must be tailored to the candidate's resume strengths and job requirements. "
            "Include related_requirements as an array of strings from the job posting. "
            "Do not include generic questions; make them specific.\n\n"
            f"Resume Data: {json.dumps(resume_data)}\n\n"
            f"Job Requirements: {json.dumps(job_requirements)}\n\n"
            f"Company Research: {json.dumps(company_research)}\n\n"
            f"Skill Gaps: {json.dumps(skill_gaps)}"
        )

    def _system_prompt(self) -> str:
        return (
            "You are an interview question generator. Create tailored, specific questions based on the provided data. "
            "Return valid JSON only, no extra text."
        )

    def _normalize_questions(self, parsed: Any) -> list[InterviewQuestion]:
        if not isinstance(parsed, list):
            raise LLMMalformedResponseError("Parsed questions must be a JSON array.")

        questions = []
        for i, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue
            try:
                question = InterviewQuestion(
                    id=item.get("id", f"q{i+1}"),
                    question=self._coerce_text(item.get("question")),
                    category=self._coerce_text(item.get("category")),
                    difficulty=self._coerce_text(item.get("difficulty")),
                    rationale=self._coerce_text(item.get("rationale")),
                    related_requirements=self._coerce_list(item.get("related_requirements")),
                )
                questions.append(question)
            except Exception:
                continue  # Skip invalid items

        if len(questions) < 3:
            raise ValueError("Generated fewer than 3 valid questions.")

        return questions[:7]

    def _coerce_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return ""
        return str(value).strip()

    def _coerce_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]
