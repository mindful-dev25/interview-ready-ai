from app.services.report_generator import ANSWERS_MARKER, insert_answers

ANSWERS = [
    {"question": "Tell me\nabout yourself.", "final_answer": "I build AI agents [evidence-1].\n\nI also lead teams [evidence-2][evidence-3]."},
    {"question": "Why this role?", "final_answer": "The mission."},
]
FULL_ANSWERS = (
    "### Question 1\n\n**Tell me about yourself.**\n\nI build AI agents.\n\nI also lead teams.\n\n"
    "### Question 2\n\n**Why this role?**\n\nThe mission."
)


def test_full_answers_replace_the_marker_and_citations_are_dropped():
    report = f"# Report\n\n## 3. Interview Questions & Answers\n\n{ANSWERS_MARKER}\n\n## 4. Coaching Tips"

    assert insert_answers(report, ANSWERS) == (
        f"# Report\n\n## 3. Interview Questions & Answers\n\n{FULL_ANSWERS}\n\n## 4. Coaching Tips"
    )


def test_full_answers_are_added_at_the_end_when_the_marker_is_missing():
    assert insert_answers("# Report", ANSWERS) == f"# Report\n\n## Interview Questions & Answers\n\n{FULL_ANSWERS}"


def test_a_repeated_marker_is_removed():
    report = insert_answers(f"{ANSWERS_MARKER}\n\nMore\n\n{ANSWERS_MARKER}", ANSWERS)

    assert ANSWERS_MARKER not in report
    assert report.count("### Question 1") == 1
