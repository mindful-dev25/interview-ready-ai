"""Parse and normalize JSON that an LLM returned as text."""

import json
import re
from typing import Any

from app.core.llm import LLMMalformedResponseError

_CODE_FENCE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n?(.*?)\n?```$", re.DOTALL)


def parse_json_response(text: str, *, expect: type, context: str) -> Any:
    """Decode an LLM reply as JSON of the expected top-level type (``dict`` or ``list``).

    Models often wrap JSON in a Markdown code fence or add a sentence around it,
    so the fence is stripped and, failing that, the outermost JSON span is tried.
    ``context`` names what was being parsed, for the error message.
    """
    candidate = text.strip()
    fenced = _CODE_FENCE.match(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        parsed = json.loads(candidate)
    except ValueError:
        parsed = None

    # Also covers a valid reply of the wrong shape, e.g. {"questions": [...]} when a list is expected.
    if not isinstance(parsed, expect):
        parsed = _parse_embedded_json(candidate, expect)

    if not isinstance(parsed, expect):
        kind = "object" if expect is dict else "array"
        raise LLMMalformedResponseError(f"The model did not return a valid JSON {kind} while {context}.")
    return parsed


def _parse_embedded_json(text: str, expect: type) -> Any | None:
    """Try the span from the first opening bracket to the last closing one."""
    opener, closer = ("{", "}") if expect is dict else ("[", "]")
    start, end = text.find(opener), text.rfind(closer)
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except ValueError:
        return None


def coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def coerce_list(value: Any) -> list[Any]:
    """Wrap a scalar in a list; keep list items as they are."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def coerce_str_list(value: Any) -> list[str]:
    """Like ``coerce_list`` but with every item stringified and blanks dropped."""
    return [text for text in (str(item).strip() for item in coerce_list(value)) if text]
