"""Tests for uploading a PDF resume and getting its text back."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.resume_pdf import MAX_RESUME_PDF_BYTES

client = TestClient(app)


def make_pdf(lines: list[str]) -> bytes:
    """Build a small one-page PDF showing the given lines, without needing a PDF-writing library."""
    shown = " ".join(f"({line}) Tj T*" for line in lines)
    content = f"BT /F1 12 Tf 72 720 Td 14 TL {shown} ET".encode()
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


def upload(content: bytes, filename: str = "resume.pdf", content_type: str = "application/pdf"):
    return client.post("/api/resume/extract", files={"file": (filename, content, content_type)})


def test_extract_returns_the_text_of_a_pdf_resume():
    response = upload(make_pdf(["Jane Doe", "Senior Engineer at Example Corp", "Skills: Python, FastAPI"]))

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "resume.pdf"
    assert body["page_count"] == 1
    assert body["text"].splitlines() == ["Jane Doe", "Senior Engineer at Example Corp", "Skills: Python, FastAPI"]


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
