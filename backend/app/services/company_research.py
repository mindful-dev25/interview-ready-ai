import json
import re
from typing import Any

from app.core.llm import GroqLLMClient, LLMGenerationError, LLMMalformedResponseError


class CompanyResearchService:
    """Extract company research from job posting text."""

    def __init__(self, llm_client: GroqLLMClient | None = None) -> None:
        self.llm = llm_client or GroqLLMClient()

    async def research(self, company_name: str, job_page_text: str) -> dict[str, Any]:
        if not company_name or not company_name.strip():
            raise ValueError("Company name is required for research.")

        if not job_page_text or not job_page_text.strip():
            return self._empty_research(company_name)

        prompt = self._build_prompt(company_name, job_page_text)
        response = await self.llm.generate(prompt=prompt, system_prompt=self._system_prompt())

        try:
            parsed = json.loads(response)
        except ValueError as exc:
            raise LLMMalformedResponseError(
                "Groq returned invalid JSON while researching company."
            ) from exc

        return self._normalize_research(parsed, company_name)

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
            f"Job posting text:\n{job_page_text.strip()}"
        )

    def _system_prompt(self) -> str:
        return (
            "You are a company research assistant. Extract only factual information from the provided text. "
            "Do not add external knowledge or assumptions. Return valid JSON only."
        )

    def _normalize_research(self, parsed: Any, company_name: str) -> dict[str, Any]:
        if not isinstance(parsed, dict):
            raise LLMMalformedResponseError("Parsed company research must be a JSON object.")

        return {
            "company_name": self._coerce_text(parsed.get("company_name")) or company_name,
            "website": self._coerce_text(parsed.get("website")),
            "summary": self._coerce_text(parsed.get("summary")),
            "products": self._coerce_list(parsed.get("products")),
            "values": self._coerce_list(parsed.get("values")),
            "recent_highlights": self._coerce_list(parsed.get("recent_highlights")),
            "interview_signals": self._coerce_list(parsed.get("interview_signals")),
            "evidence": self._coerce_list(parsed.get("evidence")),
        }

    def _empty_research(self, company_name: str) -> dict[str, Any]:
        return {
            "company_name": company_name,
            "website": "",
            "summary": "",
            "products": [],
            "values": [],
            "recent_highlights": [],
            "interview_signals": [],
            "evidence": [],
        }

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

