"""Tidy LLM report markdown for the narrow report panel, which renders plain markdown without tables."""

import re

_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
_BULLET_PREFIX = re.compile(r"^[•\-*·]\s*")


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _is_separator(row: str) -> bool:
    cells = [cell for cell in _cells(row) if cell]
    return bool(cells) and all(_SEPARATOR_CELL.match(cell) for cell in cells)


def _list_items(cell: str) -> list[str]:
    """Split a cell that holds a list (``<br>``-separated or bullet-prefixed) into items."""
    parts = [_BULLET_PREFIX.sub("", part).strip() for part in _BR.split(cell)]
    return [part for part in parts if part]


def _is_list_cell(cell: str) -> bool:
    return bool(_BR.search(cell)) or cell.startswith("•")


def _table_to_list(rows: list[str]) -> list[str]:
    """One block per data row: the short cells as a bold title, list-like cells as bullets."""
    body = [row for row in rows if not _is_separator(row)]
    has_header = len(rows) > 1 and _is_separator(rows[1])
    if has_header:
        body = body[1:]

    lines: list[str] = []
    for row in body:
        cells = [cell for cell in _cells(row) if cell]
        title = [cell for cell in cells if not _is_list_cell(cell)]
        items = [item for cell in cells if _is_list_cell(cell) for item in _list_items(cell)]
        if items:
            if title:
                lines += [f"**{' · '.join(title)}**", ""]
            lines += [f"- {item}" for item in items]
        else:
            lines.append(f"- {' · '.join(title)}")
        lines.append("")
    return lines


def tidy_report_markdown(markdown: str) -> str:
    """Turn markdown tables into headed bullet lists and ``<br>`` tags into line breaks."""
    output: list[str] = []
    table: list[str] = []

    def flush_table() -> None:
        if table:
            output.extend(_table_to_list(table))
            table.clear()

    for line in markdown.splitlines():
        if _TABLE_ROW.match(line):
            table.append(line)
            continue
        flush_table()
        output.append(_BR.sub("\n", line))
    flush_table()

    return re.sub(r"\n{3,}", "\n\n", "\n".join(output)).strip()
