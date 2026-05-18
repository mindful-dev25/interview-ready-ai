import asyncio
import json

from pydantic import HttpUrl

from app.services.job_scraper import JobScraper


class DummyLLM:
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return json.dumps(
            {
                "title": "Software Engineer",
                "company": "Example Corp",
                "location": "Remote",
                "responsibilities": ["Build and maintain APIs."],
                "required_skills": ["Python", "APIs"],
                "preferred_skills": ["RAG", "AI"],
                "keywords": ["software", "engineering", "cloud"],
                "raw_text": "Example job posting text.",
            }
        )


def test_extract_readable_text_filters_markup():
    html = """
    <html>
      <head><script>console.log('x')</script></head>
      <body><header>Should remove</header><div>Job title: Software Engineer</div></body>
    </html>
    """
    scraper = JobScraper(llm_client=DummyLLM())
    text = scraper._extract_readable_text(html)

    assert "Job title: Software Engineer" in text
    assert "Should remove" not in text


def test_scrape_returns_normalized_job_description():
    async def fake_fetch_html(url: str) -> str:
        return "<html><body><h1>Software Engineer</h1><p>Join our team building software products.</p></body></html>"

    scraper = JobScraper(llm_client=DummyLLM())
    scraper._fetch_html = fake_fetch_html

    job_url = HttpUrl.build(scheme="http", host="example.com", path="/careers/software-engineer")
    result = asyncio.run(scraper.scrape(job_url))

    assert result["title"] == "Software Engineer"
    assert result["company"] == "Example Corp"
    assert result["location"] == "Remote"
    assert "Build and maintain APIs." in result["responsibilities"]
