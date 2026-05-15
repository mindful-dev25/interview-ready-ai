import json
from typing import Any

from app.core.llm import GroqLLMClient, LLMGenerationError, LLMMalformedResponseError
from app.core.prompts import ANSWER_DRAFT_PROMPT
from app.schemas import EvidenceItem, InterviewAnswer, InterviewQuestion
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
                evidence=evidence_formatted,
            )

            response = await self.llm.generate(prompt=prompt, system_prompt=self._system_prompt())

            parsed = self._parse_response(response)
            answer = self._build_answer(question, evidence, parsed)
            answers.append(answer)

        return answers

    def _system_prompt(self) -> str:
        return (
            "You are an interview answer drafter. Use only the provided evidence to draft answers. "
            "Cite evidence IDs and avoid unsupported claims."
        )

    def _parse_response(self, response: str) -> dict[str, Any]:
        # Simple parsing, assuming the response follows the format
        lines = response.strip().split('\n')
        parsed = {}
        current_key = None
        for line in lines:
            if line.startswith('- Draft Answer:'):
                current_key = 'draft_answer'
                parsed[current_key] = line.replace('- Draft Answer:', '').strip()
            elif line.startswith('- Rationale:'):
                current_key = 'rationale'
                parsed[current_key] = line.replace('- Rationale:', '').strip()
            elif line.startswith('- Confidence:'):
                parsed['confidence'] = float(line.replace('- Confidence:', '').strip())
            elif line.startswith('- Evidence Used:'):
                evidence_ids = line.replace('- Evidence Used:', '').strip().split(',')
                parsed['evidence_used'] = [id.strip() for id in evidence_ids if id.strip()]
            elif current_key and line.strip():
                parsed[current_key] += ' ' + line.strip()

        return parsed

    def _build_answer(
        self,
        question: InterviewQuestion,
        evidence: list[dict[str, Any]],
        parsed: dict[str, Any],
    ) -> InterviewAnswer:
        evidence_used = []
        for item in evidence:
            if item.get('id') in parsed.get('evidence_used', []):
                evidence_used.append(
                    EvidenceItem(
                        id=item['id'],
                        source_type=item.get('source_type', 'unknown'),
                        source=item.get('source', 'Unknown'),
                        quote=item.get('quote', ''),
                        relevance=item.get('relevance', ''),
                        score=item.get('score'),
                        metadata=item.get('metadata', {}),
                    )
                )

        return InterviewAnswer(
            id=f"a{question.id[1:]}",  # e.g., q1 -> a1
            question=question,
            draft_answer=parsed.get('draft_answer', ''),
            evidence_used=evidence_used,
            rationale=parsed.get('rationale', ''),
            # confidence could be added to schema if needed
        )
