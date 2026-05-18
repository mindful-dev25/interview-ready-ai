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

## Current Scope

- Exposes a health check endpoint.
- Provides a placeholder analysis endpoint.
- Defines service boundaries for resume parsing, job scraping, company research, RAG, guardrails, and report generation.
- Defines placeholders for LangGraph orchestration, Groq-backed LLM access, Chroma storage, and session storage.

Full implementation is intentionally deferred.
