# Upper bound on scraped page text placed in a prompt, to bound token cost and context size.
MAX_PAGE_TEXT_CHARS = 12_000


def truncate_for_prompt(text: str, limit: int = MAX_PAGE_TEXT_CHARS) -> str:
    return text if len(text) <= limit else text[:limit]


SYSTEM_PROMPT = """
You are Interview Ready AI, a local interview preparation assistant.
Use only grounded resume, job description, and retrieved company evidence.
Flag uncertainty instead of inventing experience, credentials, or facts.
"""

# Shared by drafting and revision so every answer reads the same way.
PLAIN_ENGLISH_RULES = """
Write in plain, easy English that anyone can follow on the first read:
- Use short sentences, about 15 words or fewer each. One idea per sentence.
- Use everyday words. Say "use" not "leverage", "help" not "facilitate", "cut" not "reduce expenditure".
- Avoid jargon. If you must name a technical thing, say what it does in a few simple words.
- Sound like a person talking in an interview, not like a report.
- If the question asks several things, answer each part in order, one or two sentences per part.
"""

ANSWER_DRAFT_PROMPT = """
Draft a confident, first-person interview answer for the question below.
Keep it to 3-5 short sentences. Be direct and specific, with no filler phrases.
""" + PLAIN_ENGLISH_RULES + """
If resume or job evidence is provided, use it to make the answer personal. Cite each evidence ID in its own
brackets right after the sentence it supports, like [evidence_id] or [id_one][id_two]. Never put several IDs
in one pair of brackets, and never cite an ID that is not in the evidence list.
If no evidence is available, write a strong general answer that shows the skill. Never use placeholder brackets
or incomplete sentences.

Question: {question}

Evidence:
{evidence}

Output format:
- Draft Answer: [the answer]
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
Keep any [evidence_id] citations that still support a sentence, each in its own brackets.
""" + PLAIN_ENGLISH_RULES + """
Return only the revised answer text with no preamble or labels.
"""
