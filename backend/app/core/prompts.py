# Upper bound on scraped page text placed in a prompt, to bound token cost and context size.
MAX_PAGE_TEXT_CHARS = 12_000


def truncate_for_prompt(text: str, limit: int = MAX_PAGE_TEXT_CHARS) -> str:
    return text if len(text) <= limit else text[:limit]


SYSTEM_PROMPT = """
You are Interview Ready AI, a local interview preparation assistant.
Use only grounded resume, job description, and retrieved company evidence.
Flag uncertainty instead of inventing experience, credentials, or facts.
"""

ANSWER_DRAFT_PROMPT = """
Draft a concise, confident, first-person interview answer for the question below.
Keep the answer to 2-3 sentences maximum. Be direct and specific — no filler phrases.

If resume or job evidence is provided, use it to make the answer personal and cite evidence IDs in brackets like [evidence_id].
If no evidence is available, write a strong 2-3 sentence general answer that demonstrates the competency. Never use placeholder brackets or incomplete sentences.

Question: {question}

Evidence:
{evidence}

Output format:
- Draft Answer: [2-3 sentence answer]
- Rationale: [one sentence]
- Confidence: [0.0 to 1.0]
- Evidence Used: [comma-separated evidence IDs, or "none"]
"""

REVISION_PROMPT = """
You are an expert interview coach. Rewrite the interview answer below based on the reviewer's feedback.

Question: {question}

Current answer:
{draft_answer}

Reviewer feedback:
{reviewer_notes}

Write an improved answer that directly addresses the feedback. Be specific, concise, and authentic.
Return only the revised answer text with no preamble or labels.
"""
