"""Build the documents indexed for retrieval: resume, job posting, and company research."""

from typing import Any

from app.schemas import CompanyResearch, JobRequirements


def build_context_documents(
    resume_text: str | None,
    job_data: dict[str, Any],
    job_requirements: JobRequirements,
    company_research: CompanyResearch,
) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    if resume_text and resume_text.strip():
        documents.append({"content": resume_text, "source_type": "resume", "source": "Resume"})

    job_context = "\n".join(filter(None, [
        job_data.get("raw_text", ""),
        *job_data.get("responsibilities", []),
        *job_data.get("required_skills", []),
        *job_data.get("preferred_skills", []),
    ]))
    if job_context.strip():
        role_label = f"{job_requirements.title or 'Role'} at {job_requirements.company or 'Company'}"
        documents.append({"content": job_context, "source_type": "job_description", "source": role_label})

    if company_research.summary:
        company_context = " ".join(filter(None, [
            company_research.summary,
            *company_research.values,
            *company_research.recent_highlights,
        ]))
        source = job_data.get("company") or "Company"
        documents.append({"content": company_context, "source_type": "company_research", "source": source})

    return documents
