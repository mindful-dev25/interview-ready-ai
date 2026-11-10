"""Extract the text of an uploaded PDF resume."""

import logging
import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

logger = logging.getLogger(__name__)

MAX_RESUME_PDF_BYTES = 5 * 1024 * 1024
_PDF_SIGNATURE = b"%PDF-"
# Some writers put a few bytes before the signature; readers accept it within the first kilobyte.
_SIGNATURE_SEARCH_BYTES = 1024
_TRAILING_SPACES = re.compile(r"[ \t]+\n")
_BLANK_RUNS = re.compile(r"\n{3,}")


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
        pages = [page.extract_text() or "" for page in reader.pages]
    except ResumePdfError:
        raise
    except Exception as exc:
        # pypdf raises many different errors on damaged or unusual files; all of them mean the same to the user.
        logger.warning("Could not read uploaded resume PDF.", exc_info=True)
        raise ResumePdfError(
            "This PDF could not be read. Try exporting it again or paste the resume text instead."
        ) from exc

    text = _tidy("\n\n".join(page.strip() for page in pages if page.strip()))
    if not text:
        raise ResumePdfError(
            "No text was found in this PDF. It may be a scanned image; paste the resume text instead."
        )
    return ResumePdfText(text=text, page_count=len(pages))


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _TRAILING_SPACES.sub("\n", text)
    return _BLANK_RUNS.sub("\n\n", text).strip()
