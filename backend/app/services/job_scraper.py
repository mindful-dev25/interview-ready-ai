from pydantic import HttpUrl


class JobScraper:
    """Placeholder job description scraper."""

    async def scrape(self, job_url: HttpUrl) -> dict[str, str]:
        # TODO: Fetch and normalize job title, company, responsibilities, and requirements.
        return {"url": str(job_url), "description": ""}
