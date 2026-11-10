import asyncio
import logging
import re
from typing import Any

from app.core.llm import GroqLLMClient
from app.core.prompts import ANSWER_DRAFT_PROMPT
from app.schemas import EvidenceItem, EvidenceSourceType, InterviewAnswer, InterviewQuestion
from app.services.guardrails import GuardrailService
from app.services.rag import RAGService

logger = logging.getLogger(__name__)

# Drafts run concurrently, capped to stay under the LLM provider's rate limits.
MAX_CONCURRENT_DRAFTS = 4
EVIDENCE_PER_QUESTION = 5

_SYSTEM_PROMPT = (
    "You are an expert interview coach. Draft concise, confident, first-person interview answers. "
    "When resume evidence is available, make answers specific and personal. "
    "When no evidence is available, write strong general answers that demonstrate the competency — "
    "never use placeholder brackets or leave sentences incomplete."
)

# Labels of the line-based reply format requested by ANSWER_DRAFT_PROMPT.
_DRAFT_LABEL = "draft answer:"
_RATIONALE_LABEL = "rationale:"
_CONFIDENCE_LABEL = "confidence:"
_EVIDENCE_LABEL = "evidence used:"
_CITATION = re.compile(r"\[([^\]]+)\]")


class AnswerDrafter:
    """Draft interview answers using RAG and Groq, optionally checking each with guardrails."""

    def __init__(
        self,
        rag_service: RAGService | None = None,
        llm_client: GroqLLMClient | None = None,
        guardrails: GuardrailService | None = None,
        max_concurrency: int = MAX_CONCURRENT_DRAFTS,
    ) -> None:
        self.rag = rag_service or RAGService()
        self.llm = llm_client or GroqLLMClient()
        self.guardrails = guardrails
        self.max_concurrency = max(1, max_concurrency)

    async def draft_answers(
        self,
        session_id: str,
        questions: list[InterviewQuestion],
        resume_text: str | None = None,
    ) -> list[InterviewAnswer]:
        """Draft one answer per question, concurrently, returned in question order."""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def draft(question: InterviewQuestion) -> InterviewAnswer:
            async with semaphore:
                return await self._draft_answer(session_id, question, resume_text)

        return list(await asyncio.gather(*(draft(question) for question in questions)))

    async def _draft_answer(
        self,
        session_id: str,
        question: InterviewQuestion,
        resume_text: str | None,
    ) -> InterviewAnswer:
        try:
            evidence = await self.rag.retrieve(session_id, question.question, limit=EVIDENCE_PER_QUESTION)
        except Exception:
            logger.warning("Evidence retrieval failed for question %s.", question.id, exc_info=True)
            evidence = []

        prompt = ANSWER_DRAFT_PROMPT.format(
            question=question.question,
            evidence=self.rag.format_evidence_for_prompt(evidence) or "No resume or job evidence available.",
        )
        try:
            response = await self.llm.generate(prompt=prompt, system_prompt=_SYSTEM_PROMPT)
            parsed = self._parse_response(response)
        except Exception:
            logger.warning("Drafting failed for question %s.", question.id, exc_info=True)
            parsed = {"draft_answer": ""}

        answer = self._build_answer(question, evidence, parsed)
        await self._apply_guardrails(answer, evidence, resume_text)
        return answer

    async def _apply_guardrails(
        self,
        answer: InterviewAnswer,
        evidence: list[dict[str, Any]],
        resume_text: str | None,
    ) -> None:
        if self.guardrails is None or not answer.draft_answer:
            return
        try:
            # The rewrite suggestion costs an extra LLM call per flagged answer, so it is skipped here.
            review = await self.guardrails.review_answer(
                answer.draft_answer, evidence, resume_text, suggest_rewrite=False
            )
        except Exception:
            logger.warning("Guardrail review failed for answer %s.", answer.id, exc_info=True)
            return

        answer.truthfulness_guardrail = review["truthfulness_result"]
        answer.citation_guardrail = review["citation_result"]
        answer.suggested_safe_rewrite = review["suggested_safe_rewrite"]

    def _parse_response(self, response: str) -> dict[str, Any]:
        """Parse the labelled-line reply; fall back to the whole reply as the draft."""
        parsed: dict[str, Any] = {}
        current_key: str | None = None

        for raw_line in response.strip().split("\n"):
            line = raw_line.strip()
            label_line = line.lstrip("-* ").lower()
            value = line.split(":", 1)[1].strip().strip("*").strip() if ":" in line else ""

            if label_line.startswith(_DRAFT_LABEL):
                current_key = "draft_answer"
                parsed[current_key] = value
            elif label_line.startswith(_RATIONALE_LABEL):
                current_key = "rationale"
                parsed[current_key] = value
            elif label_line.startswith(_CONFIDENCE_LABEL):
                current_key = None
                try:
                    parsed["confidence"] = float(value)
                except ValueError:
                    pass
            elif label_line.startswith(_EVIDENCE_LABEL):
                current_key = None
                parsed["evidence_used"] = [
                    evidence_id.strip().strip("[]") for evidence_id in value.split(",") if evidence_id.strip()
                ]
            elif current_key and line:
                parsed[current_key] = f"{parsed.get(current_key, '')} {line}".strip()

        if not parsed.get("draft_answer"):
            parsed["draft_answer"] = response.strip()

        return parsed

    def _build_answer(
        self,
        question: InterviewQuestion,
        evidence: list[dict[str, Any]],
        parsed: dict[str, Any],
    ) -> InterviewAnswer:
        draft_answer = parsed.get("draft_answer", "")
        # Count evidence the model listed as used and evidence it cited inline as [id].
        used_ids = set(parsed.get("evidence_used", [])) | {
            match.strip() for match in _CITATION.findall(draft_answer)
        }

        answer_id = "a" + question.id[1:] if question.id.startswith("q") else f"a_{question.id}"
        return InterviewAnswer(
            id=answer_id,
            question=question,
            draft_answer=draft_answer,
            evidence_used=[
                self._to_evidence_item(item) for item in evidence if item.get("id") in used_ids
            ],
        )

    @staticmethod
    def _to_evidence_item(item: dict[str, Any]) -> EvidenceItem:
        try:
            source_type = EvidenceSourceType(item.get("source_type", "generated"))
        except ValueError:
            source_type = EvidenceSourceType.generated

        return EvidenceItem(
            id=item["id"],
            source_type=source_type,
            source=item.get("source", "Unknown"),
            quote=item.get("quote", ""),
            relevance=item.get("relevance", ""),
            score=item.get("score"),
            metadata=item.get("metadata", {}),
        )
