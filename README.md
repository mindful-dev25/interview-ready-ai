# Interview Ready AI

Interview Ready AI is a Claude-backed, agentic RAG application for interview preparation. Users upload a resume and provide a job description URL, then the app drafts tailored interview answers with guardrails, evidence, and human-in-the-loop review before a final report is generated.

<img width="1035" height="2214" alt="template" src="https://github.com/user-attachments/assets/0989fd8e-66f9-45d7-9d1e-5286d60ab1ae" />

## Tech Stack

- Backend: Python, FastAPI
- Orchestration: an async analysis pipeline (scrape, parse, research, index, generate, draft, check)
- LLM provider: Claude via the Anthropic Python SDK
- Retrieval: local keyword index stored as JSON files
- Frontend: Next.js, React, TypeScript
- Styling: Tailwind CSS
- UI components: shadcn/ui

## Project Structure

```text
backend/   FastAPI API, analysis pipeline, RAG and guardrail services, and storage adapters
frontend/  Next.js app shell and interview-prep UI components
```

## Local Setup

### Backend

```bash
cd backend
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload
```

Dependencies are managed with [uv](https://docs.astral.sh/uv/). `uv sync` creates `backend/.venv` with the Python version in `.python-version` and the exact package versions in `uv.lock`.

The backend runs at `http://localhost:8000` by default.

Set `ANTHROPIC_API_KEY` in `backend/.env` before using LLM generation. Create the key in the Claude Console; a claude.ai subscription does not include API access. `CLAUDE_MODEL` selects the model and defaults to `claude-opus-5-5`.

Note: Retrieval and session persistence are local, file-based services. LLM generation uses the Claude API.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The frontend runs at `http://localhost:3000` by default.
