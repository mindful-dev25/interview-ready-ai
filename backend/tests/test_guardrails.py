import asyncio

from fakes import FakeLLM

from app.services.guardrails import GuardrailService

UNCITED_CLAIM = "I led a team that built a new billing platform for our enterprise customers."
RESUME_EVIDENCE = [{"id": "evidence-1", "source_type": "resume", "quote": "Built the API gateway."}]


def review(service: GuardrailService, answer: str, **kwargs):
    return asyncio.run(service.review_answer(answer, **kwargs))


def test_uncited_personal_claim_is_flagged_and_rewritten():
    service = GuardrailService(llm_client=FakeLLM("A safer answer."))

    result = review(service, UNCITED_CLAIM, evidence=[])

    assert not result["truthfulness_result"].passed
    assert result["citation_result"].missing_citation_claims == [UNCITED_CLAIM]
    assert result["suggested_safe_rewrite"] == "A safer answer."


def test_rewrite_can_be_skipped_to_avoid_the_llm_call():
    llm = FakeLLM("A safer answer.")

    result = review(GuardrailService(llm_client=llm), UNCITED_CLAIM, evidence=[], suggest_rewrite=False)

    assert not result["truthfulness_result"].passed
    assert result["suggested_safe_rewrite"] is None
    assert llm.prompts == []


def test_answer_citing_resume_evidence_passes():
    llm = FakeLLM()
    answer = "During the migration I built the API gateway [evidence-1]."

    result = review(GuardrailService(llm_client=llm), answer, evidence=RESUME_EVIDENCE)

    assert result["truthfulness_result"].passed
    assert result["citation_result"].passed
    assert result["citation_result"].cited_evidence_ids == ["evidence-1"]
    assert result["suggested_safe_rewrite"] is None
    assert llm.prompts == []


def test_sensitive_information_is_flagged():
    result = review(
        GuardrailService(llm_client=FakeLLM()),
        "You can reach me at jane@example.com any time.",
        evidence=[],
        suggest_rewrite=False,
    )

    explanations = [claim.explanation for claim in result["truthfulness_result"].claims]
    assert any("sensitive" in explanation for explanation in explanations)


def test_resume_check_is_skipped_when_no_resume_was_provided():
    result = review(
        GuardrailService(llm_client=FakeLLM()), UNCITED_CLAIM, evidence=[], suggest_rewrite=False
    )

    explanations = [claim.explanation for claim in result["truthfulness_result"].claims]
    assert not any("resume" in explanation for explanation in explanations)
