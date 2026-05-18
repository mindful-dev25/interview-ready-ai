from app.core.llm import GroqLLMClient, LLMGenerationError
from app.core.prompts import REVISION_PROMPT, SYSTEM_PROMPT
from app.schemas import InterviewAnswer


class AnswerReviser:
    def __init__(self) -> None:
        self._llm = GroqLLMClient()

    async def revise(self, answer: InterviewAnswer, reviewer_notes: str) -> str:
        prompt = REVISION_PROMPT.format(
            question=answer.question.question,
            draft_answer=answer.draft_answer,
            reviewer_notes=reviewer_notes,
        )
        try:
            return await self._llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        except LLMGenerationError:
            raise
