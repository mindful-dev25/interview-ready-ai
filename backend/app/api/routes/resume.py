from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.schemas import ResumeTextResponse
from app.services.resume_pdf import (
    MAX_RESUME_PDF_BYTES,
    ResumePdfError,
    extract_resume_pdf_text,
    looks_like_pdf,
)

router = APIRouter(tags=["resume"])


@router.post("/resume/extract", response_model=ResumeTextResponse)
async def extract_resume_text(file: UploadFile) -> ResumeTextResponse:
    """Turn an uploaded PDF resume into text the client can show, edit and send to /analysis."""
    # Read one byte past the limit so an oversized file is detected without loading all of it.
    content = await file.read(MAX_RESUME_PDF_BYTES + 1)
    if len(content) > MAX_RESUME_PDF_BYTES:
        limit_mb = MAX_RESUME_PDF_BYTES // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"The PDF is larger than {limit_mb} MB.")
    if not looks_like_pdf(content):
        raise HTTPException(status_code=415, detail="Only PDF files can be uploaded here.")

    try:
        # Parsing is CPU-bound, so keep it off the event loop.
        result = await run_in_threadpool(extract_resume_pdf_text, content)
    except ResumePdfError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ResumeTextResponse(text=result.text, filename=file.filename, page_count=result.page_count)
