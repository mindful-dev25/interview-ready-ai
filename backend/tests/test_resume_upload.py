"""Tests for uploading a PDF resume and getting its text back."""

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.main import app
from app.services.resume_pdf import MAX_RESUME_PDF_BYTES, tidy_resume_text

client = TestClient(app)


def build_pdf(content: bytes) -> bytes:
    """Wrap a page content stream in a minimal one-page PDF, without needing a PDF-writing library."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref_offset = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        pdf += b"%010d 00000 n \n" % offset
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref_offset)
    return bytes(pdf)


def make_pdf(lines: list[str]) -> bytes:
    """A PDF that shows each line with one text operation, the way most PDF writers do."""
    shown = " ".join(f"({line}) Tj T*" for line in lines)
    return build_pdf(f"BT /F1 12 Tf 72 720 Td 14 TL {shown} ET".encode())


def make_google_docs_style_pdf(lines: list[str]) -> bytes:
    """A PDF laid out like a Google Docs export.

    The page is flipped, and every word and every space is its own text block
    that first resets the position to the origin and then moves to the word.
    """
    blocks = ["1 0 0 -1 0 792 cm"]
    for row, line in enumerate(lines):
        x = 72.0
        y = 80 + row * 16
        for piece in line.replace(" ", "\n \n").split("\n"):
            blocks.append(f"BT /F1 12 Tf 1 0 0 -1 0 0 Tm {x:.1f} {-y} Td ({piece}) Tj ET")
            x += 3.3 if piece == " " else 6.2 * len(piece)
    return build_pdf("\n".join(blocks).encode())


def upload(content: bytes, filename: str = "resume.pdf", content_type: str = "application/pdf"):
    return client.post("/api/resume/extract", files={"file": (filename, content, content_type)})


def test_extract_returns_the_text_of_a_pdf_resume():
    response = upload(make_pdf(["Jane Doe", "Senior Engineer at Example Corp", "Skills: Python, FastAPI"]))

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "resume.pdf"
    assert body["page_count"] == 1
    assert body["text"].splitlines() == ["Jane Doe", "Senior Engineer at Example Corp", "Skills: Python, FastAPI"]


def test_extract_keeps_lines_together_in_a_google_docs_style_pdf():
    lines = ["Jane Doe", "Senior AI Engineer", "Saved $200K in annual revenue"]
    pdf = make_google_docs_style_pdf(lines)
    # Without help, the PDF library puts every word of such a file on its own line.
    assert len(PdfReader(BytesIO(pdf)).pages[0].extract_text().split("\n")) > 3 * len(lines)

    response = upload(pdf)

    assert response.status_code == 200
    assert response.json()["text"].splitlines() == lines


def test_tidy_resume_text_cleans_up_extraction_artifacts():
    raw = "Jane  Doe \r\nBuilt workﬂows for ﬁnance , saving $200K .\n\n\n\n●  Led a team"

    assert tidy_resume_text(raw) == "Jane Doe\nBuilt workflows for finance, saving $200K.\n\n● Led a team"


def test_extract_rejects_a_file_that_is_not_a_pdf():
    response = upload(b"Jane Doe\nSenior Engineer", filename="resume.pdf")

    assert response.status_code == 415
    assert "Only PDF files" in response.json()["detail"]


def test_extract_rejects_a_pdf_over_the_size_limit():
    response = upload(b"%PDF-1.4\n" + b"0" * MAX_RESUME_PDF_BYTES)

    assert response.status_code == 413
    assert "larger than 5 MB" in response.json()["detail"]


def test_extract_explains_when_a_pdf_has_no_text():
    response = upload(make_pdf([]))

    assert response.status_code == 422
    assert "No text was found" in response.json()["detail"]


def test_extract_explains_when_a_pdf_is_damaged():
    response = upload(b"%PDF-1.4\nthis is not really a pdf")

    assert response.status_code == 422
    assert "could not be read" in response.json()["detail"]
