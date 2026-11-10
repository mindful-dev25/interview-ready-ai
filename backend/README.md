# Interview Ready AI Backend

FastAPI backend for the Interview Ready AI Groq-backed interview preparation workflow.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Testing

```bash
cd backend
pytest
```

The tests run offline: web fetches and LLM calls are replaced by fakes.

## What It Does

- `POST /api/analysis` runs the pipeline in `app/services/analysis_pipeline.py`: scrape the job posting, parse the resume, research the company, index the context, generate questions, then draft an answer per question. Drafts run concurrently and each is checked by the guardrail heuristics in `app/services/guardrails/`.
- `POST /api/review` and `POST /api/revision` record human review of each answer.
- `GET /api/report/{session_id}` generates the final report once every answer is approved or edited.
- Sessions are JSON files under `SESSION_STORE_PATH`; the retrieval index is JSON files under `CHROMA_PERSIST_DIR`.

Each pipeline step falls back to a generic result if it fails. Failures are logged, and those the user should know about are returned in `metadata.warnings`.
