import asyncio

from fakes import FakeLLM

from app.schemas import InterviewQuestion
from app.services.answer_drafter import AnswerDrafter
from app.services.guardrails import GuardrailService
from app.services.rag import RAGService
from app.storage.vector_store import VectorStore

REPLY = (
    "- Draft Answer: I built Python APIs for the billing team [{evidence_id}].\n"
    "- Rationale: Shows direct experience.\n"
    "- Confidence: 0.8\n"
    "- Evidence Used: none"
)


class SlowLLM:
    """Records how many generate() calls overlap."""

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return "- Draft Answer: A solid general answer."


def questions(count: int) -> list[InterviewQuestion]:
    return [InterviewQuestion(id=f"q{i}", question=f"Question {i}?") for i in range(1, count + 1)]


def rag_for(tmp_path) -> RAGService:
    return RAGService(VectorStore(persist_dir=str(tmp_path)))


def test_drafts_run_concurrently_within_the_limit_and_keep_question_order(tmp_path):
    llm = SlowLLM()
    drafter = AnswerDrafter(rag_service=rag_for(tmp_path), llm_client=llm, max_concurrency=2)

    answers = asyncio.run(drafter.draft_answers("session", questions(6)))

    assert [answer.id for answer in answers] == ["a1", "a2", "a3", "a4", "a5", "a6"]
    assert all(answer.draft_answer == "A solid general answer." for answer in answers)
    assert llm.peak == 2


def test_evidence_cited_inline_is_attached_and_guardrails_run(tmp_path):
    rag = rag_for(tmp_path)
    resume = "Built Python APIs for the billing team."

    async def run():
        await rag.index_context("session", [{"content": resume, "source_type": "resume", "source": "Resume"}])
        evidence_id = (await rag.retrieve("session", "python"))[0]["id"]
        llm = FakeLLM(REPLY.format(evidence_id=evidence_id))
        drafter = AnswerDrafter(rag_service=rag, llm_client=llm, guardrails=GuardrailService(llm_client=llm))
        answers = await drafter.draft_answers("session", questions(1), resume_text=resume)
        return evidence_id, answers[0], llm

    evidence_id, answer, llm = asyncio.run(run())

    assert [item.id for item in answer.evidence_used] == [evidence_id]
    assert answer.citation_guardrail.passed
    assert answer.citation_guardrail.cited_evidence_ids == [evidence_id]
    assert answer.truthfulness_guardrail.summary
    # One call for the draft; the guardrail check itself must not call the LLM.
    assert len(llm.prompts) == 1


def test_failed_draft_yields_empty_answer_instead_of_raising(tmp_path):
    class BrokenLLM:
        async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
            raise RuntimeError("LLM down")

    drafter = AnswerDrafter(rag_service=rag_for(tmp_path), llm_client=BrokenLLM())

    answers = asyncio.run(drafter.draft_answers("session", questions(2)))

    assert [answer.draft_answer for answer in answers] == ["", ""]
