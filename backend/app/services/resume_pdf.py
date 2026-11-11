"""Extract the text of an uploaded PDF resume."""

import logging
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from pypdf import PageObject, PdfReader
from pypdf.generic import ContentStream, FloatObject, NameObject

logger = logging.getLogger(__name__)

MAX_RESUME_PDF_BYTES = 5 * 1024 * 1024
_PDF_SIGNATURE = b"%PDF-"
# Some writers put a few bytes before the signature; readers accept it within the first kilobyte.
_SIGNATURE_SEARCH_BYTES = 1024

# Single glyphs some fonts use for letter pairs; spelled out so "ﬁnance" still matches "finance".
_LIGATURES = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"})
_SPACE_RUNS = re.compile(r"[ \t\u00a0]+")
_SPACE_BEFORE_PUNCTUATION = re.compile(r" +([.,;:!?])")
_BLANK_RUNS = re.compile(r"\n{3,}")

Operation = tuple[list[Any], bytes]


class ResumePdfError(ValueError):
    """Raised with a user-facing message when a PDF resume cannot be turned into text."""


@dataclass(frozen=True)
class ResumePdfText:
    text: str
    page_count: int


def looks_like_pdf(content: bytes) -> bool:
    return _PDF_SIGNATURE in content[:_SIGNATURE_SEARCH_BYTES]


def extract_resume_pdf_text(content: bytes) -> ResumePdfText:
    """Return the text of every page, or raise ResumePdfError explaining what to do instead."""
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ResumePdfError(
                "This PDF is password-protected. Save an unprotected copy or paste the resume text instead."
            )
        pages = [_page_text(page, reader) for page in reader.pages]
    except ResumePdfError:
        raise
    except Exception as exc:
        # pypdf raises many different errors on damaged or unusual files; all of them mean the same to the user.
        logger.warning("Could not read uploaded resume PDF.", exc_info=True)
        raise ResumePdfError(
            "This PDF could not be read. Try exporting it again or paste the resume text instead."
        ) from exc

    text = tidy_resume_text("\n\n".join(pages))
    if not text:
        raise ResumePdfError(
            "No text was found in this PDF. It may be a scanned image; paste the resume text instead."
        )
    return ResumePdfText(text=text, page_count=len(pages))


def tidy_resume_text(text: str) -> str:
    """Clean extracted text: spell out ligatures, collapse stray spaces and blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").translate(_LIGATURES)
    lines = [_SPACE_BEFORE_PUNCTUATION.sub(r"\1", _SPACE_RUNS.sub(" ", line)).strip() for line in text.split("\n")]
    return _BLANK_RUNS.sub("\n\n", "\n".join(lines)).strip()


def _page_text(page: PageObject, reader: PdfReader) -> str:
    raw_content = page.get("/Contents")
    if raw_content is not None:
        # "bytes" keeps text strings raw, as pypdf itself does, so the fonts' character maps still apply.
        content = ContentStream(raw_content.get_object(), reader, "bytes")
        content.operations = _merge_position_resets(content.operations)
        page[NameObject("/Contents")] = content
    return page.extract_text() or ""


def _merge_position_resets(operations: list[Operation]) -> list[Operation]:
    """Fold each "set text matrix, then move" pair into one "set text matrix".

    Google Docs exports start a new text block for every word: `Tm` puts the
    position back at the origin and `Td` then moves to the word. pypdf decides
    on line breaks after each positioning operator, so it sees the stop at the
    origin as a jump to another line and puts every word on its own line.
    Applying the move to the matrix up front describes the same position
    without that intermediate stop.
    """
    merged: list[Operation] = []
    for operands, operator in operations:
        previous = merged[-1] if merged else None
        if operator == b"Td" and previous is not None and previous[1] == b"Tm":
            matrix = _numbers(previous[0], 6)
            move = _numbers(operands, 2)
            if matrix is not None and move is not None:
                a, b, c, d, e, f = matrix
                tx, ty = move
                moved = [a, b, c, d, tx * a + ty * c + e, tx * b + ty * d + f]
                merged[-1] = ([FloatObject(value) for value in moved], b"Tm")
                continue
        merged.append((operands, operator))
    return merged


def _numbers(operands: list[Any], count: int) -> list[float] | None:
    if len(operands) != count or not all(isinstance(operand, (int, float)) for operand in operands):
        return None
    return [float(operand) for operand in operands]
