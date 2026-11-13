import asyncio
import json

import httpx
import pytest
from fakes import FakeLLM

from app.services import job_scraper
from app.services.job_scraper import JobFetchError, JobScraper

JOB_JSON = json.dumps(
    {
        "title": "Software Engineer",
        "company": "Example Corp",
        "location": "Remote",
        "responsibilities": ["Build and maintain APIs."],
        "required_skills": ["Python", "APIs"],
        "preferred_skills": ["RAG", "AI"],
        "keywords": ["software", "engineering", "cloud"],
    }
)

JOB_HTML = (
    "<html><body><h1>Software Engineer</h1>"
    "<p>Join our team building software products used by thousands of customers every day. "
    "You will design, build and maintain APIs, work closely with product managers, "
    "and help shape our engineering practices.</p></body></html>"
)
JOB_TEXT = "Example Corp is hiring a Software Engineer.\n\n" + "You will build and maintain cloud APIs. " * 5
PASTE_HINT = "Paste the job description into the box under the URL and analyze again."


def scraper_with_page(html: str = JOB_HTML) -> JobScraper:
    async def fake_fetch_html(url: str) -> str:
        return html

    scraper = JobScraper(llm_client=FakeLLM())
    scraper._fetch_html = fake_fetch_html
    return scraper


def respond_with(monkeypatch, status: int) -> None:
    """Make every HTTP request the scraper sends come back with the given status."""
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(status))
    monkeypatch.setattr(job_scraper.httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))


def test_extract_readable_text_filters_markup():
    html = """
    <html>
      <head><script>console.log('x')</script></head>
      <body><header>Should remove</header><div>Job title: Software Engineer</div></body>
    </html>
    """
    text = JobScraper(llm_client=FakeLLM())._extract_readable_text(html)

    assert "Job title: Software Engineer" in text
    assert "Should remove" not in text


def test_fetch_text_returns_the_readable_text_of_the_page():
    text = asyncio.run(scraper_with_page().fetch_text("http://example.com/careers/software-engineer"))

    assert text.startswith("Software Engineer Join our team")
    assert "<p>" not in text


def test_fetch_text_stops_when_the_site_refuses_automated_access(monkeypatch):
    respond_with(monkeypatch, 406)

    with pytest.raises(JobFetchError) as error:
        asyncio.run(JobScraper(llm_client=FakeLLM()).fetch_text("https://jobs.example.com/1"))

    assert str(error.value) == f"The job site refused automated access (HTTP 406). {PASTE_HINT}"


def test_fetch_text_stops_when_the_page_is_missing(monkeypatch):
    respond_with(monkeypatch, 404)

    with pytest.raises(JobFetchError) as error:
        asyncio.run(JobScraper(llm_client=FakeLLM()).fetch_text("https://jobs.example.com/missing"))

    assert str(error.value) == f"Failed to fetch job posting: HTTP 404. {PASTE_HINT}"


def test_fetch_text_stops_when_the_page_has_too_little_text():
    scraper = scraper_with_page("<html><body><p>Please sign in to continue.</p></body></html>")

    with pytest.raises(JobFetchError, match="too little readable text") as error:
        asyncio.run(scraper.fetch_text("http://example.com/job"))

    assert str(error.value).endswith(PASTE_HINT)


def test_parse_text_returns_normalized_job_description():
    llm = FakeLLM(JOB_JSON)

    result = asyncio.run(JobScraper(llm_client=llm).parse_text(JOB_TEXT, "http://example.com/job"))

    assert result["title"] == "Software Engineer"
    assert result["company"] == "Example Corp"
    assert result["location"] == "Remote"
    assert "Build and maintain APIs." in result["responsibilities"]
    assert result["warning"] is None
    assert "\n" not in result["raw_text"]
    assert "Source: http://example.com/job" in llm.prompts[0]


def test_parse_text_marks_pasted_text_that_has_no_url():
    llm = FakeLLM(JOB_JSON)

    asyncio.run(JobScraper(llm_client=llm).parse_text(JOB_TEXT))

    assert "Source: pasted by the user" in llm.prompts[0]


def test_parse_text_accepts_json_wrapped_in_a_code_fence():
    result = asyncio.run(JobScraper(llm_client=FakeLLM(f"```json\n{JOB_JSON}\n```")).parse_text(JOB_TEXT))

    assert result["title"] == "Software Engineer"


def test_parse_text_falls_back_with_warning_when_llm_reply_is_not_json():
    result = asyncio.run(JobScraper(llm_client=FakeLLM("Sorry, I cannot help with that.")).parse_text(JOB_TEXT))

    assert result["title"] == ""
    assert result["raw_text"].startswith("Example Corp is hiring")
    assert result["warning"]


def test_parse_text_warns_when_the_description_is_too_short():
    llm = FakeLLM(JOB_JSON)

    result = asyncio.run(JobScraper(llm_client=llm).parse_text("Software Engineer, remote"))

    assert result["title"] == ""
    assert "too short" in result["warning"]
    assert llm.prompts == []


def test_long_text_is_truncated_in_the_prompt():
    llm = FakeLLM(JOB_JSON)

    result = asyncio.run(JobScraper(llm_client=llm).parse_text("engineering " * 5000))

    assert len(llm.prompts[0]) < 13_000
    assert len(result["raw_text"]) > 50_000
