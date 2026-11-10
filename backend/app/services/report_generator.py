import logging
from typing import Any

from app.core.llm import GroqLLMClient, LLMGenerationError
from app.schemas import (
    CompanyResearch,
    HumanReviewStatus,
    InterviewAnswer,
    JobRequirements,
    SessionState,
)

logger = logging.getLogger(__name__)

# Answers a human has signed off on, either as drafted or after editing.
REVIEWED_STATUSES = (HumanReviewStatus.approved, HumanReviewStatus.edited)

_SYSTEM_PROMPT = (
    "You are a concise report writer. Produce a clear markdown final report "
    "from the provided approved interview answers and role/company context. "
    "Do not invent new candidate details or include unapproved drafts."
)
_COACHING_TIPS = [
    "Keep answers concise and tie each example to measurable impact.",
    "Use evidence-backed details when describing contributions and outcomes.",
    "Highlight how your experience maps to the role's key requirements.",
    "Ask thoughtful questions that show curiosity about the team and product.",
]
_QUESTIONS_FOR_INTERVIEWER = [
    "What are the immediate priorities for this role in the first 90 days?",
    "How does the team measure success for someone in this position?",
    "What challenges is the team currently facing that this role would help solve?",
]
_NO_RISKS_NOTE = "No unresolved risks or gaps were identified for the approved answers."


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


class ReportGenerator:
    """Generate a polished final report from approved interview answers."""

    def __init__(self, llm_client: GroqLLMClient | None = None) -> None:
        self.llm = llm_client or GroqLLMClient()

    async def generate(self, session: SessionState) -> str:
        approved_answers = [
            answer for answer in session.answers if answer.human_status in REVIEWED_STATUSES
        ]
        if not approved_answers:
            raise ValueError("No approved or edited answers found for report generation.")

        context = self._build_report_context(session, approved_answers)

        try:
            markdown = await self.llm.generate(
                prompt=self._build_report_prompt(context), system_prompt=_SYSTEM_PROMPT
            )
            if markdown.strip():
                return markdown.strip()
        except (LLMGenerationError, ValueError):
            logger.warning("LLM report generation failed; using the template report.", exc_info=True)

        return self._build_fallback_report(context)

    def _build_report_context(
        self, session: SessionState, approved_answers: list[InterviewAnswer]
    ) -> dict[str, Any]:
        job = session.job_requirements or JobRequirements(source_url="")
        company = session.company_research or CompanyResearch()

        return {
            "target_role": job.title or "Target role",
            "target_company": job.company or company.company_name or "Target company",
            "job_summary": job.summary or "",
            "top_requirements": [
                requirement
                for requirement in (
                    job.seniority,
                    *job.required_skills,
                    *job.preferred_skills,
                    *job.responsibilities,
                )
                if requirement
            ],
            "company_summary": company.summary or "",
            "approved_answers": [
                {
                    "question": answer.question.question,
                    "final_answer": answer.final_answer or answer.draft_answer,
                    "evidence": [
                        {
                            "id": item.id,
                            "source_type": item.source_type.value,
                            "source": item.source,
                            "quote": item.quote,
                        }
                        for item in answer.evidence_used
                    ],
                }
                for answer in approved_answers
            ],
            "evidence_notes": self._compile_evidence_notes(approved_answers),
            "unresolved_risks": self._compile_unresolved_risks(approved_answers),
        }

    def _compile_evidence_notes(self, approved_answers: list[InterviewAnswer]) -> list[str]:
        notes: dict[str, None] = {}  # insertion-ordered set
        for answer in approved_answers:
            for item in answer.evidence_used:
                notes[f"[{item.id}] {item.source_type.value} - {item.source}: {item.quote}"] = None
        return list(notes)

    def _compile_unresolved_risks(self, approved_answers: list[InterviewAnswer]) -> list[str]:
        risks: dict[str, None] = {}  # insertion-ordered set
        for answer in approved_answers:
            for claim in answer.truthfulness_guardrail.claims:
                if claim.explanation:
                    risks[claim.explanation] = None
            for note in answer.citation_guardrail.weak_citation_notes:
                risks[note] = None
        return list(risks) or [_NO_RISKS_NOTE]

    @staticmethod
    def _evidence_lines(answer: dict[str, Any]) -> list[str]:
        return [
            f"- [{item['id']}] {item['quote']} ({item['source_type']} from {item['source']})"
            for item in answer["evidence"]
        ]

    def _build_report_prompt(self, context: dict[str, Any]) -> str:
        answer_blocks = []
        for answer in context["approved_answers"]:
            block = f"### {answer['question']}\n{answer['final_answer']}"
            evidence_lines = self._evidence_lines(answer)
            if evidence_lines:
                block += "\nEvidence:\n" + "\n".join(evidence_lines)
            answer_blocks.append(block)

        return (
            "Create a polished markdown final report using only the approved answers and context below. "
            "Do not invent new candidate details or include any draft answers that were not approved or edited. "
            "Organize the report with clear headings and concise sections.\n\n"
            f"Target Role: {context['target_role']}\n"
            f"Target Company: {context['target_company']}\n\n"
            f"Job Summary:\n{context['job_summary']}\n\n"
            f"Top Job Requirements:\n{_bullets(context['top_requirements'])}\n\n"
            f"Company Summary:\n{context['company_summary']}\n\n"
            "Approved Interview Answers:\n" + "\n".join(answer_blocks) + "\n\n"
            "Evidence Notes:\n"
            f"{_bullets(context['evidence_notes']) or '- No evidence citations were available.'}\n\n"
            f"Coaching Tips:\n{_bullets(_COACHING_TIPS)}\n\n"
            f"Questions to Ask the Interviewer:\n{_bullets(_QUESTIONS_FOR_INTERVIEWER)}\n\n"
            f"Unresolved Risks / Gaps:\n{_bullets(context['unresolved_risks'])}\n"
        )

    def _build_fallback_report(self, context: dict[str, Any]) -> str:
        """Template report used when the LLM is unavailable."""
        lines = [
            f"# Final Interview Report for {context['target_role']} at {context['target_company']}",
            "",
            "## Top Job Requirements",
            _bullets(context["top_requirements"]),
            "",
            "## Candidate Positioning Summary",
            context["job_summary"] or "The candidate is positioned for the target role based on the approved answers.",
            "",
            "## Approved Interview Answers",
        ]

        for answer in context["approved_answers"]:
            lines += [f"### {answer['question']}", answer["final_answer"], ""]
            evidence_lines = self._evidence_lines(answer)
            if evidence_lines:
                lines += ["Evidence notes:", *evidence_lines, ""]

        lines += [
            "## Coaching Tips",
            _bullets(_COACHING_TIPS),
            "",
            "## Questions to Ask the Interviewer",
            _bullets(_QUESTIONS_FOR_INTERVIEWER),
            "",
            "## Unresolved Risks / Gaps",
            _bullets(context["unresolved_risks"]),
        ]
        return "\n".join(lines)
