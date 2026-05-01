from typing import TypedDict


class InterviewPrepState(TypedDict, total=False):
    session_id: str
    resume_text: str
    job_description: str
    company_research: str
    retrieved_evidence: list[dict[str, str]]
    draft_answers: list[dict[str, str]]
    guardrail_findings: list[str]
    human_feedback: list[str]
    final_report: str


def build_interview_prep_graph() -> object:
    # TODO: Define the LangGraph workflow:
    # parse resume -> scrape job -> research company -> retrieve evidence ->
    # draft answers -> run guardrails -> request human review -> generate report.
    return {"status": "TODO: LangGraph workflow placeholder"}
