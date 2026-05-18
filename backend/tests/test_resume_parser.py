import asyncio
import json

from app.services.resume_parser import ResumeParser


class DummyLLM:
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return json.dumps(
            {
                "candidate_summary": "Experienced software engineer with strong AI delivery experience.",
                "skills": ["Python", "APIs", "RAG"],
                "tools_technologies": ["Docker", "Kubernetes"],
                "projects": ["Interview prep automation"],
                "work_experience": ["Built backend systems for candidate-facing applications."],
                "measurable_achievements": ["Improved answer generation accuracy by 30%."],
                "education_certifications": ["B.S. Computer Science"],
            }
        )


def test_parse_text_returns_structured_resume():
    resume_text = (
        "Summary:\nExperienced software engineer with AI and interview prep delivery experience. "
        "I have led multiple product launches and supported candidate-facing tools in production. "
        "Experience:\nWorked at Example Corp building reliable backend systems, leading integrations, and automating candidate workflows. "
        "I collaborated with teams to improve product metrics and optimize release cadence. "
        "Skills:\nPython, APIs, RAG, cloud architecture, automation, and data-driven decision making. "
        "Education:\nB.S. Computer Science, Example University. "
        "Projects:\nDeveloped an interview assistant that generated evidence-based answers for users, boosting usability and reducing time to prepare."
    )

    parser = ResumeParser(llm_client=DummyLLM())
    parsed = asyncio.run(parser.parse_text(resume_text))

    assert parsed["candidate_summary"] == "Experienced software engineer with strong AI delivery experience."
    assert "Python" in parsed["skills"]
    assert parsed["education_certifications"] == ["B.S. Computer Science"]
    assert parsed["work_experience"] == ["Built backend systems for candidate-facing applications."]
