import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup, Comment

from app.core.llm import GroqLLMClient, LLMGenerationError
from app.core.llm_json import coerce_str_list, coerce_text, parse_json_response
from app.core.prompts import truncate_for_prompt

logger = logging.getLogger(__name__)

# Pages shorter than this are almost certainly not a job posting (login wall, error page).
MIN_JOB_TEXT_WORDS = 20

_NOISE_TAGS = ["script", "style", "noscript", "header", "footer", "nav", "form", "iframe", "svg"]
_NOISE_ATTRIBUTES = ["class", "id", "role", "aria-label"]
_NOISE_PATTERN = re.compile(r"(nav|footer|header|banner|advert|promo|cookie|popup|modal)", re.I)
_WHITESPACE = re.compile(r"\s+")

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_SYSTEM_PROMPT = (
    "You are a job posting parser. Extract structured job requirements exactly as valid JSON. "
    "Do not add any extra text or markdown."
)


class JobFetchError(Exception):
    """Raised when the job posting URL cannot be fetched from the remote server."""


class JobScraper:
    """Fetch and normalize job descriptions from career pages.

    Scraping never fails the analysis: when the page can't be fetched or
    structured, empty job data is returned with a ``warning`` explaining why.
    """

    def __init__(self, llm_client: GroqLLMClient | None = None, timeout: float = 20.0) -> None:
        self.llm = llm_client or GroqLLMClient()
        self.timeout = timeout

    async def scrape(self, job_url: str) -> dict[str, Any]:
        url = str(job_url)
        try:
            html = await self._fetch_html(url)
        except JobFetchError as exc:
            logger.warning("Job posting fetch failed for %s: %s", url, exc)
            return self._empty_job_data(
                warning=f"{exc} Questions are not tailored to this posting."
            )

        text = self._extract_readable_text(html)
        if len(text.split()) < MIN_JOB_TEXT_WORDS:
            return self._empty_job_data(
                text,
                warning=(
                    "The job page had too little readable text (it may need a login or JavaScript). "
                    "Questions are not tailored to this posting."
                ),
            )

        try:
            raw_json = await self.llm.generate(
                prompt=self._build_prompt(text, url), system_prompt=_SYSTEM_PROMPT
            )
            parsed = parse_json_response(raw_json, expect=dict, context="structuring the job posting")
        except LLMGenerationError as exc:
            logger.warning("Could not structure job posting %s: %s", url, exc)
            return self._empty_job_data(
                text,
                warning="The job posting could not be analyzed in detail, so questions may be generic.",
            )

        return self._normalize_job_description(parsed, text)

    async def _fetch_html(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": _USER_AGENT})
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise JobFetchError(
                f"Failed to fetch job posting: HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise JobFetchError(f"Failed to fetch job posting: {exc}.") from exc

        return response.text

    def _extract_readable_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        for element in soup.find_all(_NOISE_TAGS):
            element.decompose()

        for attribute in _NOISE_ATTRIBUTES:
            for element in soup.find_all(attrs={attribute: _NOISE_PATTERN}):
                element.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        body = soup.body or soup
        visible_text = body.get_text(separator=" ", strip=True)
        return _WHITESPACE.sub(" ", visible_text).strip()

    def _build_prompt(self, readable_text: str, url: str) -> str:
        return (
            "Extract a structured job description from the following text. "
            "Return only valid JSON with the fields: title, company, location, responsibilities, "
            "required_skills, preferred_skills, keywords. "
            "Use strings for title, company, and location. Use arrays for responsibilities, "
            "required_skills, preferred_skills, and keywords. "
            "If a field is missing, return an empty string or empty array. Do not include any markdown or commentary.\n\n"
            f"Job posting text:\n{truncate_for_prompt(readable_text)}\n\nSource URL: {url}"
        )

    def _normalize_job_description(self, parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
        return {
            "title": coerce_text(parsed.get("title")),
            "company": coerce_text(parsed.get("company")),
            "location": coerce_text(parsed.get("location")),
            "responsibilities": coerce_str_list(parsed.get("responsibilities")),
            "required_skills": coerce_str_list(parsed.get("required_skills")),
            "preferred_skills": coerce_str_list(parsed.get("preferred_skills")),
            "keywords": coerce_str_list(parsed.get("keywords")),
            "raw_text": raw_text,
            "warning": None,
        }

    def _empty_job_data(self, raw_text: str = "", warning: str | None = None) -> dict[str, Any]:
        return {
            "title": "",
            "company": "",
            "location": "",
            "responsibilities": [],
            "required_skills": [],
            "preferred_skills": [],
            "keywords": [],
            "raw_text": raw_text,
            "warning": warning,
        }
