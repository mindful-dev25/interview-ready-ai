from app.core.llm import GroqLLMClient
from app.core.prompts import REVISION_PROMPT, SYSTEM_PROMPT
from app.schemas import InterviewAnswer


class AnswerReviser:
    """Rewrite a drafted answer according to the reviewer's notes."""

    def __init__(self, llm_client: GroqLLMClient | None = None) -> None:
        self.llm = llm_client or GroqLLMClient()

    async def revise(self, answer: InterviewAnswer, reviewer_notes: str) -> str:
        prompt = REVISION_PROMPT.format(
            question=answer.question.question,
            draft_answer=answer.draft_answer,
            reviewer_notes=reviewer_notes,
        )
        return await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
