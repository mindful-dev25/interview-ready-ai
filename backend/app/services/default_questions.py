"""Fixed interview questions that bookend generated ones, plus a fallback set."""

from app.schemas import InterviewQuestion

# Generated questions are numbered after the two fixed opening questions.
FIRST_GENERATED_QUESTION_NUMBER = 3


def _question(id: str, question: str, category: str, difficulty: str, rationale: str) -> InterviewQuestion:
    return InterviewQuestion(
        id=id,
        question=question,
        category=category,
        difficulty=difficulty,
        rationale=rationale,
        related_requirements=[],
    )


def opening_questions() -> list[InterviewQuestion]:
    return [
        _question("q1", "Tell me about yourself.", "introduction", "easy", "Opens the interview."),
        _question("q2", "Why are you interested in this role?", "motivation", "easy", "Reveals role alignment."),
    ]


def closing_question(question_id: str) -> InterviewQuestion:
    return _question(
        question_id,
        "What questions do you have for us?",
        "candidate_questions",
        "easy",
        "Shows curiosity and preparation.",
    )


def fallback_questions() -> list[InterviewQuestion]:
    """Generic questions used when LLM question generation fails."""
    return [
        _question("q3", "Tell me about a time you solved a challenging technical problem.", "behavioral", "medium", "Evaluates problem-solving."),
        _question("q4", "How do you prioritize tasks when facing multiple deadlines?", "strategy", "medium", "Assesses time management."),
        _question("q5", "Describe a project you're most proud of.", "behavioral", "medium", "Shows ownership and impact."),
        _question("q6", "How do you handle feedback and code review?", "behavioral", "easy", "Evaluates collaboration."),
        _question("q7", "Tell me about a time you disagreed with a team decision.", "behavioral", "medium", "Tests conflict resolution."),
        _question("q8", "How do you approach learning a new codebase or technology?", "growth", "easy", "Shows learning agility."),
        _question("q9", "Describe a time you delivered under tight constraints.", "behavioral", "hard", "Tests judgment under pressure."),
    ]


def wrap_with_standard_questions(generated: list[InterviewQuestion]) -> list[InterviewQuestion]:
    """Renumber generated questions and bookend them with the standard opener/closer."""
    for i, question in enumerate(generated):
        question.id = f"q{i + FIRST_GENERATED_QUESTION_NUMBER}"

    closing_id = f"q{len(generated) + FIRST_GENERATED_QUESTION_NUMBER}"
    return [*opening_questions(), *generated, closing_question(closing_id)]
