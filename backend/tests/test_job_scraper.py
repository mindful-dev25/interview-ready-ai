import asyncio
import json

from fakes import FakeLLM

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


def scraper_with_page(llm: FakeLLM, html: str = JOB_HTML) -> JobScraper:
    async def fake_fetch_html(url: str) -> str:
        return html

    scraper = JobScraper(llm_client=llm)
    scraper._fetch_html = fake_fetch_html
    return scraper


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


def test_scrape_returns_normalized_job_description():
    scraper = scraper_with_page(FakeLLM(JOB_JSON))

    result = asyncio.run(scraper.scrape("http://example.com/careers/software-engineer"))

    assert result["title"] == "Software Engineer"
    assert result["company"] == "Example Corp"
    assert result["location"] == "Remote"
    assert "Build and maintain APIs." in result["responsibilities"]
    assert result["warning"] is None


def test_scrape_accepts_json_wrapped_in_a_code_fence():
    scraper = scraper_with_page(FakeLLM(f"```json\n{JOB_JSON}\n```"))

    result = asyncio.run(scraper.scrape("http://example.com/job"))

    assert result["title"] == "Software Engineer"


def test_scrape_falls_back_with_warning_when_page_cannot_be_fetched():
    async def failing_fetch(url: str) -> str:
        raise JobFetchError("Failed to fetch job posting: HTTP 404.")

    llm = FakeLLM(JOB_JSON)
    scraper = JobScraper(llm_client=llm)
    scraper._fetch_html = failing_fetch

    result = asyncio.run(scraper.scrape("http://example.com/missing"))

    assert result["title"] == ""
    assert "HTTP 404" in result["warning"]
    assert llm.prompts == []


def test_scrape_falls_back_with_warning_when_llm_reply_is_not_json():
    scraper = scraper_with_page(FakeLLM("Sorry, I cannot help with that."))

    result = asyncio.run(scraper.scrape("http://example.com/job"))

    assert result["title"] == ""
    assert result["raw_text"].startswith("Software Engineer")
    assert result["warning"]


def test_long_pages_are_truncated_in_the_prompt():
    llm = FakeLLM(JOB_JSON)
    long_html = f"<html><body><p>{'engineering ' * 5000}</p></body></html>"
    scraper = scraper_with_page(llm, long_html)

    result = asyncio.run(scraper.scrape("http://example.com/job"))

    assert len(llm.prompts[0]) < 13_000
    assert len(result["raw_text"]) > 50_000
