# Interview Ready AI

Interview Ready AI is a local-LLM, agentic RAG application for interview preparation. Users upload a resume and provide a job description URL, then the app drafts tailored interview answers with guardrails, evidence, and human-in-the-loop review before a final report is generated.

## Tech Stack

- Backend: Python, FastAPI
- Agent orchestration: LangGraph
- Local LLM: Ollama
- Vector DB: Chroma
- Frontend: Next.js, React, TypeScript
- Styling: Tailwind CSS
- UI components: shadcn/ui

## Project Structure

```text
backend/   FastAPI API, agent graph, RAG services, and storage adapters
frontend/  Next.js app shell and interview-prep UI components
```

## Local Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000` by default.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The frontend runs at `http://localhost:3000` by default.

### Local LLM

Install and run Ollama, then pull a local model:

```bash
ollama pull llama3.1
```

Update `backend/.env` if you want to use a different local model.

## Status

This is the initial skeleton. Core workflows, agent nodes, retrieval logic, guardrails, persistence, and report generation are intentionally stubbed with TODOs for future implementation.
