import json
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup, Comment

from app.core.llm import GroqLLMClient, LLMGenerationError, LLMMalformedResponseError


class JobFetchError(Exception):
    """Raised when the job posting URL cannot be fetched from the remote server."""


class JobScraper:
    """Fetch and normalize job descriptions from career pages."""

    def __init__(self, llm_client: GroqLLMClient | None = None, timeout: float = 20.0) -> None:
        self.llm = llm_client or GroqLLMClient()
        self.timeout = timeout

    async def scrape(self, job_url: str) -> dict[str, Any]:
        url = job_url
        try:
            html = await self._fetch_html(url)
        except JobFetchError:
            return self._empty_job_data()

        text = self._extract_readable_text(html)

        if len(text.split()) < 20:
            return self._empty_job_data(text)

        try:
            raw_json = await self._structure_job_description(text, url)
            parsed = self._parse_json(raw_json)
            return self._normalize_job_description(parsed, text)
        except (JobFetchError, LLMMalformedResponseError):
            return self._empty_job_data(text)

    async def _fetch_html(self, url: str) -> str:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise JobFetchError(
                f"Failed to fetch job posting: HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise JobFetchError(
                f"Failed to fetch job posting: {exc}."
            ) from exc

        return response.text

    def _extract_readable_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for selector in ["script", "style", "noscript", "header", "footer", "nav", "form", "iframe", "svg"]:
            for element in soup.select(selector):
                element.decompose()

        for attribute in ["class", "id", "role", "aria-label"]:
            for element in soup.find_all(attrs={attribute: re.compile(r"(nav|footer|header|banner|advert|promo|cookie|popup|modal)", re.I)}):
                element.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        body = soup.body or soup
        visible_text = body.get_text(separator=" ", strip=True)
        normalized = re.sub(r"\s+", " ", visible_text).strip()
        return normalized

    async def _structure_job_description(self, readable_text: str, url: str) -> str:
        prompt = (
            "Extract a structured job description from the following text. "
            "Return only valid JSON with the fields: title, company, location, responsibilities, "
            "required_skills, preferred_skills, keywords, raw_text. "
            "Use strings for title, company, location, and raw_text. Use arrays for responsibilities, "
            "required_skills, preferred_skills, and keywords. "
            "If a field is missing, return an empty string or empty array. Do not include any markdown or commentary.\n\n"
            f"Job posting text:\n{readable_text}\n\nSource URL: {url}"
        )

        try:
            return await self.llm.generate(prompt=prompt, system_prompt=self._system_prompt())
        except (LLMGenerationError, LLMMalformedResponseError) as exc:
            raise JobFetchError(
                "Failed to structure the job posting with the LLM. "
                "Check your GROQ_API_KEY and model configuration."
            ) from exc

    def _system_prompt(self) -> str:
        return (
            "You are a job posting parser. Extract structured job requirements exactly as valid JSON. "
            "Do not add any extra text or markdown."
        )

    def _parse_json(self, raw_json: str) -> Any:
        try:
            parsed = json.loads(raw_json)
        except ValueError as exc:
            raise LLMMalformedResponseError(
                "Groq response did not contain valid JSON for the job description."
            ) from exc

        if not isinstance(parsed, dict):
            raise LLMMalformedResponseError(
                "Parsed job description must be a JSON object."
            )
        return parsed

    def _normalize_job_description(self, parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
        return {
            "title": self._coerce_text(parsed.get("title")),
            "company": self._coerce_text(parsed.get("company")),
            "location": self._coerce_text(parsed.get("location")),
            "responsibilities": self._coerce_list(parsed.get("responsibilities")),
            "required_skills": self._coerce_list(parsed.get("required_skills")),
            "preferred_skills": self._coerce_list(parsed.get("preferred_skills")),
            "keywords": self._coerce_list(parsed.get("keywords")),
            "raw_text": raw_text,
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

    def _empty_job_data(self, raw_text: str = "") -> dict[str, Any]:
        return {
            "title": "",
            "company": "",
            "location": "",
            "responsibilities": [],
            "required_skills": [],
            "preferred_skills": [],
            "keywords": [],
            "raw_text": raw_text,
        }
