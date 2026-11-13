"""Test doubles shared across the test suite. Nothing here touches the network."""

from app.schemas import HumanReviewStatus, InterviewQuestion, SessionState
from app.storage.session_store import SessionStore

DRAFT_REPLY = "- Draft Answer: I enjoy solving problems with clear, well tested code.\n- Evidence Used: none"
RESUME_TEXT = "Summary: engineer. Experience: built APIs. Skills: Python. Education: B.S. Computer Science."
GENERATED_QUESTION_COUNT = 3
# Two fixed openers, the generated questions, and one fixed closer.
EXPECTED_ANSWER_COUNT = GENERATED_QUESTION_COUNT + 3


class FakeLLM:
    """Stands in for LLMClient: returns a canned reply and records the prompts it was given."""

    def __init__(self, reply: str = "ok") -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def ensure_configured(self) -> None:
        """The fake needs no API key."""

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        self.prompts.append(prompt)
        return self.reply


JOB_PAGE_TEXT = "Example Corp is hiring a Software Engineer to build and maintain APIs."


class FakeScraper:
    """Stands in for JobScraper. Set ``fetch_error`` to make the job page unreadable."""

    def __init__(self) -> None:
        self.warning: str | None = None
        self.fetch_error: Exception | None = None
        self.fetched_urls: list[str] = []
        self.parsed_texts: list[str] = []

    async def fetch_text(self, job_url: str) -> str:
        self.fetched_urls.append(job_url)
        if self.fetch_error is not None:
            raise self.fetch_error
        return JOB_PAGE_TEXT

    async def parse_text(self, job_text: str, job_url: str = "") -> dict:
        self.parsed_texts.append(job_text)
        return {
            "title": "Software Engineer",
            "company": "Example Corp",
            "location": "Remote",
            "responsibilities": ["Build and maintain APIs."],
            "required_skills": ["Python"],
            "preferred_skills": [],
            "keywords": [],
            "raw_text": job_text,
            "warning": self.warning,
        }


class FakeResumeParser:
    async def parse_text(self, resume_text: str) -> dict:
        return {"candidate_summary": "Engineer", "skills": ["Python"]}


class FakeCompanyResearch:
    async def research(self, company_name: str, job_page_text: str) -> dict:
        return {"company_name": company_name, "summary": "Builds developer tools.", "values": ["Ownership"]}


class FakeQuestionGenerator:
    async def generate_questions(self, **kwargs) -> list[InterviewQuestion]:
        return [
            InterviewQuestion(id=f"generated-{i}", question=f"Tailored question {i}?")
            for i in range(GENERATED_QUESTION_COUNT)
        ]


class ReviserThatApprovesAnotherAnswerMeanwhile:
    """Simulates a user approving answer a1 while the LLM is still revising another answer."""

    def __init__(self, store: SessionStore) -> None:
        self.store = store

    async def revise(self, answer, reviewer_notes: str) -> str:
        session_id = self.session_id
        session = SessionState.model_validate(await self.store.load(session_id))
        session.answers[0].human_status = HumanReviewStatus.approved
        await self.store.save(session_id, session)
        return "A revised answer."
