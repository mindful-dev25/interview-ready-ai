# Interview Ready AI Backend

FastAPI backend for the Interview Ready AI Claude-backed interview preparation workflow.

## Setup

```bash
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload
```

## Testing

```bash
cd backend
uv run pytest
```

The tests run offline: web fetches and LLM calls are replaced by fakes.

## What It Does

- `POST /api/analysis` runs the pipeline in `app/services/analysis_pipeline.py`: scrape the job posting (or use a job description pasted in `job_text`, for sites that block automated access), parse the resume, research the company, index the context, generate questions, then draft an answer per question. Drafts run concurrently and each is checked by the guardrail heuristics in `app/services/guardrails/`.
- `POST /api/analysis/stream` runs the same pipeline but reports progress while it works. The response is newline-delimited JSON: `progress` events with a percent and a message, then one `result` (the `POST /api/analysis` payload) or `error` event. The frontend uses this endpoint.
- `POST /api/resume/extract` turns an uploaded PDF resume (up to 5 MB) into text, which the frontend puts in the resume box for review before analysis. Scanned PDFs without a text layer are rejected with an explanation.
- `POST /api/review` and `POST /api/revision` record human review of each answer.
- `GET /api/report/{session_id}` generates the final report once every answer is approved or edited. The report is saved with the session and rebuilt when a reviewed answer has changed since.
- `GET /api/auth` says whether `APP_PASSWORD` is set, and `POST /api/auth` checks a password. When it is set, every other route except `GET /api/health` returns 401 unless the request sends the password in the `X-App-Password` header.
- Sessions are JSON files under `SESSION_STORE_PATH`; the retrieval index is JSON files under `CHROMA_PERSIST_DIR`.

A job page that cannot be read (blocked, missing, or needing a login) stops the analysis before any LLM call, with a message asking for the job description to be pasted instead. Every later pipeline step falls back to a generic result if it fails. Failures are logged, and those the user should know about are returned in `metadata.warnings`.

## Dependencies

Dependencies are managed with [uv](https://docs.astral.sh/uv/). `pyproject.toml` lists the direct dependencies, `uv.lock` pins the exact version of every package, and `.python-version` sets the Python version (3.12). Commit all three.

```bash
uv add <package>        # add a runtime dependency
uv add --dev <package>  # add a test or tooling dependency
uv lock --upgrade       # move to the newest allowed versions, then run the tests
```
