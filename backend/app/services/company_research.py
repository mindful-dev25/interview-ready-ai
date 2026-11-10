from typing import Any

from app.core.llm import LLMClient
from app.core.llm_json import coerce_str_list, coerce_text, parse_json_response
from app.core.prompts import truncate_for_prompt

_SYSTEM_PROMPT = (
    "You are a company research assistant. Extract only factual information from the provided text. "
    "Do not add external knowledge or assumptions. Return valid JSON only."
)
_TEXT_FIELDS = ("website", "summary")
_LIST_FIELDS = ("products", "values", "recent_highlights", "interview_signals", "evidence")


class CompanyResearchService:
    """Extract company research from job posting text."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm = llm_client or LLMClient()

    async def research(self, company_name: str, job_page_text: str) -> dict[str, Any]:
        if not company_name or not company_name.strip():
            raise ValueError("Company name is required for research.")

        if not job_page_text or not job_page_text.strip():
            return self._empty_research(company_name)

        response = await self.llm.generate(
            prompt=self._build_prompt(company_name, job_page_text), system_prompt=_SYSTEM_PROMPT
        )
        parsed = parse_json_response(response, expect=dict, context="researching company")

        return {
            "company_name": coerce_text(parsed.get("company_name")) or company_name,
            **{field: coerce_text(parsed.get(field)) for field in _TEXT_FIELDS},
            **{field: coerce_str_list(parsed.get(field)) for field in _LIST_FIELDS},
        }

    def _build_prompt(self, company_name: str, job_page_text: str) -> str:
        return (
            f"Extract company research for '{company_name}' from the following job posting text. "
            "Return only valid JSON with the fields: company_name, website, summary, products, values, "
            "recent_highlights, interview_signals, evidence. "
            "Use strings for company_name, website, summary. Use arrays for products, values, "
            "recent_highlights, interview_signals, evidence. "
            "Only include information explicitly mentioned in the text. "
            "If a field is not mentioned, return an empty string or empty array. "
            "Do not invent facts or make assumptions. Mark uncertain information with '(uncertain)'.\n\n"
            f"Job posting text:\n{truncate_for_prompt(job_page_text.strip())}"
        )

    def _empty_research(self, company_name: str) -> dict[str, Any]:
        return {
            "company_name": company_name,
            **{field: "" for field in _TEXT_FIELDS},
            **{field: [] for field in _LIST_FIELDS},
        }
