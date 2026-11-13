import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup, Comment

from app.core.llm import LLMClient, LLMGenerationError
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
# Statuses sites use to turn away automated clients; retrying or changing the URL will not help.
_REFUSED_STATUS_CODES = {401, 403, 406, 429}
_PASTE_INSTEAD = "Paste the job description into the box under the URL and analyze again."
_SYSTEM_PROMPT = (
    "You are a job posting parser. Extract structured job requirements exactly as valid JSON. "
    "Do not add any extra text or markdown."
)


class JobFetchError(ValueError):
    """Raised with a user-facing message when the job page cannot be read."""


class JobScraper:
    """Read job postings from career pages and turn their text into structured data.

    Reading the page fails loudly (``fetch_text`` raises ``JobFetchError``), because
    without the posting the whole analysis would be generic. Structuring the text
    never fails: if the LLM reply is unusable, empty job data is returned with a
    ``warning`` explaining why.
    """

    def __init__(self, llm_client: LLMClient | None = None, timeout: float = 20.0) -> None:
        self.llm = llm_client or LLMClient()
        self.timeout = timeout

    async def fetch_text(self, job_url: str) -> str:
        """Return the readable text of the job page, or raise JobFetchError saying what to do instead."""
        url = str(job_url)
        try:
            html = await self._fetch_html(url)
        except JobFetchError as exc:
            logger.warning("Job posting fetch failed for %s: %s", url, exc)
            raise JobFetchError(f"{exc} {_PASTE_INSTEAD}") from exc

        text = self._extract_readable_text(html)
        if len(text.split()) < MIN_JOB_TEXT_WORDS:
            logger.warning("Job page %s had too little readable text.", url)
            raise JobFetchError(
                f"The job page had too little readable text (it may need a login or JavaScript). {_PASTE_INSTEAD}"
            )
        return text

    async def parse_text(self, job_text: str, job_url: str = "") -> dict[str, Any]:
        """Structure job description text, whether read from the page or pasted by the user."""
        text = _WHITESPACE.sub(" ", job_text).strip()
        if len(text.split()) < MIN_JOB_TEXT_WORDS:
            return self._empty_job_data(
                text,
                warning="The job description is too short to analyze, so questions may be generic.",
            )

        try:
            raw_json = await self.llm.generate(
                prompt=self._build_prompt(text, job_url), system_prompt=_SYSTEM_PROMPT
            )
            parsed = parse_json_response(raw_json, expect=dict, context="structuring the job posting")
        except LLMGenerationError as exc:
            logger.warning("Could not structure job posting %s: %s", job_url or "(pasted)", exc)
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
            status = exc.response.status_code
            if status in _REFUSED_STATUS_CODES:
                raise JobFetchError(f"The job site refused automated access (HTTP {status}).") from exc
            raise JobFetchError(f"Failed to fetch job posting: HTTP {status}.") from exc
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
            f"Job posting text:\n{truncate_for_prompt(readable_text)}\n\n"
            f"Source: {url or 'pasted by the user'}"
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
