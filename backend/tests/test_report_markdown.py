from app.services.report_markdown import tidy_report_markdown

BACKGROUND_TABLE = """## 2. Candidate Background (from Resume)

| Period | Role | Company | Key Evidence |
|---|---|---|---|
| May 2023 – Nov 2026 | Applied AI Engineer | Blackboard | • LangGraph agents<br>• $200K/yr LLM savings |
| Jul 2021 – Apr 2023 | Full Stack AI Engineer | Medtronic | • Insulin dosing platform<br/>• 91% NLP accuracy |

## 3. Next section"""


def test_table_rows_become_bold_titles_with_bullets():
    assert tidy_report_markdown(BACKGROUND_TABLE) == (
        "## 2. Candidate Background (from Resume)\n\n"
        "**May 2023 – Nov 2026 · Applied AI Engineer · Blackboard**\n\n"
        "- LangGraph agents\n"
        "- $200K/yr LLM savings\n\n"
        "**Jul 2021 – Apr 2023 · Full Stack AI Engineer · Medtronic**\n\n"
        "- Insulin dosing platform\n"
        "- 91% NLP accuracy\n\n"
        "## 3. Next section"
    )


def test_table_without_list_cells_becomes_one_bullet_per_row():
    table = "| Skill | Level |\n|---|---|\n| Python | Expert |\n| Go | Good |"

    assert tidy_report_markdown(table) == "- Python · Expert\n\n- Go · Good"


def test_br_outside_tables_becomes_a_line_break_and_plain_markdown_is_kept():
    text = "# Title\n\nFirst line<br>second line\n\n- a bullet"

    assert tidy_report_markdown(text) == "# Title\n\nFirst line\nsecond line\n\n- a bullet"
