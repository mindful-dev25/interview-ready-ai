from typing import Any

from app.core.llm import GroqLLMClient
from app.core.prompts import ANSWER_DRAFT_PROMPT
from app.schemas import EvidenceItem, EvidenceSourceType, InterviewAnswer, InterviewQuestion
from app.services.rag import RAGService


class AnswerDrafter:
    """Draft interview answers using RAG and Groq."""

    def __init__(
        self,
        rag_service: RAGService | None = None,
        llm_client: GroqLLMClient | None = None,
    ) -> None:
        self.rag = rag_service or RAGService()
        self.llm = llm_client or GroqLLMClient()

    async def draft_answers(
        self,
        session_id: str,
        questions: list[InterviewQuestion],
    ) -> list[InterviewAnswer]:
        answers = []
        for question in questions:
            evidence = await self.rag.retrieve(session_id, question.question, limit=5)
            evidence_formatted = self.rag.format_evidence_for_prompt(evidence)

            prompt = ANSWER_DRAFT_PROMPT.format(
                question=question.question,
                evidence=evidence_formatted or "No specific evidence retrieved. Answer based on general best practices.",
            )

            response = await self.llm.generate(prompt=prompt, system_prompt=self._system_prompt())
            parsed = self._parse_response(response)
            answers.append(self._build_answer(question, evidence, parsed))

        return answers

    def _system_prompt(self) -> str:
        return (
            "You are an interview answer drafter. Use the provided evidence to draft concise, "
            "specific answers. Cite evidence IDs in brackets. If no evidence is available, "
            "draft a strong general answer."
        )

    def _parse_response(self, response: str) -> dict[str, Any]:
        lines = response.strip().split("\n")
        parsed: dict[str, Any] = {}
        current_key: str | None = None

        for line in lines:
            if line.startswith("- Draft Answer:"):
                current_key = "draft_answer"
                parsed[current_key] = line.replace("- Draft Answer:", "").strip()
            elif line.startswith("- Rationale:"):
                current_key = "rationale"
                parsed[current_key] = line.replace("- Rationale:", "").strip()
            elif line.startswith("- Confidence:"):
                current_key = None
                try:
                    parsed["confidence"] = float(line.replace("- Confidence:", "").strip())
                except ValueError:
                    pass
            elif line.startswith("- Evidence Used:"):
                current_key = None
                evidence_str = line.replace("- Evidence Used:", "").strip()
                parsed["evidence_used"] = [e.strip() for e in evidence_str.split(",") if e.strip()]
            elif current_key and line.strip():
                parsed[current_key] = parsed.get(current_key, "") + " " + line.strip()

        if not parsed.get("draft_answer"):
            parsed["draft_answer"] = response.strip()

        return parsed

    def _build_answer(
        self,
        question: InterviewQuestion,
        evidence: list[dict[str, Any]],
        parsed: dict[str, Any],
    ) -> InterviewAnswer:
        evidence_ids_used = set(parsed.get("evidence_used", []))
        evidence_used = []

        for item in evidence:
            if item.get("id") in evidence_ids_used:
                try:
                    source_type = EvidenceSourceType(item.get("source_type", "generated"))
                except ValueError:
                    source_type = EvidenceSourceType.generated

                evidence_used.append(
                    EvidenceItem(
                        id=item["id"],
                        source_type=source_type,
                        source=item.get("source", "Unknown"),
                        quote=item.get("quote", ""),
                        relevance=item.get("relevance", ""),
                        score=item.get("score"),
                        metadata=item.get("metadata", {}),
                    )
                )

        answer_id = "a" + question.id[1:] if question.id.startswith("q") else f"a_{question.id}"
        return InterviewAnswer(
            id=answer_id,
            question=question,
            draft_answer=parsed.get("draft_answer", ""),
            evidence_used=evidence_used,
        )
