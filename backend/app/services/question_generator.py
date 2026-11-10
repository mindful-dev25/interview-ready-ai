import json
from typing import Any

from app.core.llm import LLMClient
from app.core.llm_json import coerce_str_list, coerce_text, parse_json_response
from app.schemas import InterviewQuestion

QUESTION_COUNT = 7
MIN_VALID_QUESTIONS = 3

_SYSTEM_PROMPT = (
    "You are an interview question generator. Create tailored, specific questions based on the provided data. "
    "Return valid JSON only, no extra text."
)


class QuestionGenerator:
    """Generate tailored interview questions using the LLM."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    async def generate_questions(
        self,
        resume_data: dict[str, Any],
        job_requirements: dict[str, Any],
        company_research: dict[str, Any],
        skill_gaps: list[str] | None = None,
    ) -> list[InterviewQuestion]:
        prompt = self._build_prompt(resume_data, job_requirements, company_research, skill_gaps or [])
        response = await self.llm.generate(prompt=prompt, system_prompt=_SYSTEM_PROMPT)
        parsed = parse_json_response(response, expect=list, context="generating questions")
        return self._normalize_questions(parsed)

    def _build_prompt(
        self,
        resume_data: dict[str, Any],
        job_requirements: dict[str, Any],
        company_research: dict[str, Any],
        skill_gaps: list[str],
    ) -> str:
        return (
            f"Generate exactly {QUESTION_COUNT} tailored interview questions based on the provided resume, "
            "job requirements, company research, and skill gaps. "
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

    def _normalize_questions(self, parsed: list[Any]) -> list[InterviewQuestion]:
        questions: list[InterviewQuestion] = []
        for i, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue
            text = coerce_text(item.get("question"))
            if not text:
                continue
            questions.append(
                InterviewQuestion(
                    id=coerce_text(item.get("id")) or f"q{i + 1}",
                    question=text,
                    category=coerce_text(item.get("category")),
                    difficulty=coerce_text(item.get("difficulty")),
                    rationale=coerce_text(item.get("rationale")),
                    related_requirements=coerce_str_list(item.get("related_requirements")),
                )
            )

        if len(questions) < MIN_VALID_QUESTIONS:
            raise ValueError(f"Generated fewer than {MIN_VALID_QUESTIONS} valid questions.")

        return questions[:QUESTION_COUNT]
