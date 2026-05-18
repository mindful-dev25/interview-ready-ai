import json
from typing import Any

from app.core.llm import GroqLLMClient, LLMMalformedResponseError, LLMGenerationError
from app.schemas import HumanReviewStatus, SessionState
from app.storage.session_store import SessionStore


class ReportGenerator:
    """Generate a polished final report from approved interview answers."""

    def __init__(
        self,
        session_store: SessionStore | None = None,
        llm_client: GroqLLMClient | None = None,
    ) -> None:
        self.session_store = session_store or SessionStore()
        self.llm = llm_client or GroqLLMClient()

    async def generate(self, session_id: str) -> str:
        state = await self.session_store.load(session_id)
        if state is None:
            raise ValueError(f"Session {session_id} not found.")

        session = SessionState.model_validate(state)
        approved_answers = [
            answer
            for answer in session.answers
            if answer.human_status in (HumanReviewStatus.approved, HumanReviewStatus.edited)
        ]

        if not approved_answers:
            raise ValueError("No approved or edited answers found for report generation.")

        report_context = self._build_report_context(session, approved_answers)
        prompt = self._build_report_prompt(report_context)

        try:
            markdown = await self.llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a concise report writer. Produce a clear markdown final report "
                    "from the provided approved interview answers and role/company context. "
                    "Do not invent new candidate details or include unapproved drafts."
                ),
            )
            if markdown.strip():
                return markdown.strip()
        except (LLMMalformedResponseError, LLMGenerationError, ValueError):
            pass

        return self._build_fallback_report(report_context)

    def _build_report_context(self, session: SessionState, approved_answers: list[Any]) -> dict[str, Any]:
        job = session.job_requirements
        company = session.company_research
        evidence_notes = self._compile_evidence_notes(approved_answers)
        unresolved_risks = self._compile_unresolved_risks(approved_answers)

        return {
            "session_id": session.session_id,
            "target_role": job.title or "Target role",
            "target_company": job.company or company.company_name or "Target company",
            "job_summary": job.summary or "",
            "top_requirements": [
                *([job.seniority] if job.seniority else []),
                *job.required_skills,
                *job.preferred_skills,
                *job.responsibilities,
            ],
            "company_summary": company.summary or "",
            "approved_answers": [
                {
                    "question": answer.question.question,
                    "final_answer": answer.final_answer or answer.draft_answer,
                    "human_status": answer.human_status,
                    "evidence": [
                        {
                            "id": item.id,
                            "source_type": item.source_type,
                            "source": item.source,
                            "quote": item.quote,
                        }
                        for item in answer.evidence_used
                    ],
                    "truthfulness_notes": [
                        claim.explanation for claim in answer.truthfulness_guardrail.claims if claim.explanation
                    ],
                    "citation_notes": answer.citation_guardrail.weak_citation_notes,
                }
                for answer in approved_answers
            ],
            "evidence_notes": evidence_notes,
            "coaching_tips": [
                "Keep answers concise and tie each example to measurable impact.",
                "Use evidence-backed details when describing contributions and outcomes.",
                "Highlight how your experience maps to the role's key requirements.",
                "Ask thoughtful questions that show curiosity about the team and product.",
            ],
            "company_research": {
                "company_name": company.company_name,
                "values": company.values,
                "recent_highlights": company.recent_highlights,
            },
            "unresolved_risks": unresolved_risks,
        }

    def _compile_evidence_notes(self, approved_answers: list[Any]) -> list[str]:
        notes: list[str] = []
        seen = set()
        for answer in approved_answers:
            for item in answer.evidence_used:
                note = f"[{item.id}] {item.source_type} - {item.source}: {item.quote}"
                if note not in seen:
                    seen.add(note)
                    notes.append(note)
        return notes

    def _compile_unresolved_risks(self, approved_answers: list[Any]) -> list[str]:
        risks: list[str] = []
        for answer in approved_answers:
            for claim in answer.truthfulness_guardrail.claims:
                if claim.explanation and claim.explanation not in risks:
                    risks.append(claim.explanation)
            for note in answer.citation_guardrail.weak_citation_notes:
                if note not in risks:
                    risks.append(note)
        if not risks:
            risks.append("No unresolved risks or gaps were identified for the approved answers.")
        return risks

    def _build_report_prompt(self, context: dict[str, Any]) -> str:
        top_requirements = "\n".join(f"- {req}" for req in context["top_requirements"] if req)
        approved_answer_blocks = []
        for answer in context["approved_answers"]:
            evidence = "\n".join(
                f"  - {item['id']}: {item['quote']} ({item['source_type']} from {item['source']})"
                for item in answer["evidence"]
            )
            evidence_block = f"Evidence:\n{evidence}" if evidence else ""
            approved_answer_blocks.append(
                f"### {answer['question']}\n{answer['final_answer']}\n{evidence_block}"
            )

        evidence_notes = "\n".join(f"- {note}" for note in context["evidence_notes"])
        unresolved_risks = "\n".join(f"- {risk}" for risk in context["unresolved_risks"])
        coaching_tips = "\n".join(f"- {tip}" for tip in context["coaching_tips"])

        return (
            "Create a polished markdown final report using only the approved answers and context below. "
            "Do not invent new candidate details or include any draft answers that were not approved or edited. "
            "Organize the report with clear headings and concise sections.\n\n"
            f"Target Role: {context['target_role']}\n"
            f"Target Company: {context['target_company']}\n\n"
            "Job Summary:\n"
            f"{context['job_summary']}\n\n"
            "Top Job Requirements:\n"
            f"{top_requirements}\n\n"
            "Company Summary:\n"
            f"{context['company_summary']}\n\n"
            "Approved Interview Answers:\n"
            f"{chr(10).join(approved_answer_blocks)}\n\n"
            "Evidence Notes:\n"
            f"{evidence_notes or '- No evidence citations were available.'}\n\n"
            "Coaching Tips:\n"
            f"{coaching_tips}\n\n"
            "Questions to Ask the Interviewer:\n"
            "- What are the immediate priorities for this role in the first 90 days?\n"
            "- How does the team measure success for someone in this position?\n"
            "- What challenges is the team currently facing that this role would help solve?\n\n"
            "Unresolved Risks / Gaps:\n"
            f"{unresolved_risks}\n"
        )

    def _build_fallback_report(self, context: dict[str, Any]) -> str:
        report_lines = [
            f"# Final Interview Report for {context['target_role']} at {context['target_company']}",
            "",
            "## Top Job Requirements",
        ]
        report_lines.extend(f"- {req}" for req in context["top_requirements"] if req)
        report_lines.extend([
            "",
            "## Candidate Positioning Summary",
            context["job_summary"] or "The candidate is positioned for the target role based on the approved answers.",
            "",
            "## Approved Interview Answers",
        ])

        for answer in context["approved_answers"]:
            report_lines.extend([
                f"### {answer['question']}",
                answer['final_answer'],
                "",
            ])
            if answer["evidence"]:
                report_lines.append("Evidence notes:")
                report_lines.extend(
                    f"- [{item['id']}] {item['quote']} ({item['source_type']} from {item['source']})"
                    for item in answer["evidence"]
                )
                report_lines.append("")

        report_lines.extend([
            "## Coaching Tips",
            *context["coaching_tips"],
            "",
            "## Questions to Ask the Interviewer",
            "- What are the immediate priorities for this role in the first 90 days?",
            "- How does the team define success for this position?",
            "- What can I do to quickly add value in the first six months?",
            "",
            "## Unresolved Risks / Gaps",
        ])
        report_lines.extend(f"- {risk}" for risk in context["unresolved_risks"])
        return "\n".join(report_lines)
