# Interview Ready AI

Interview Ready AI is a Groq-backed, agentic RAG application for interview preparation. Users upload a resume and provide a job description URL, then the app drafts tailored interview answers with guardrails, evidence, and human-in-the-loop review before a final report is generated.

<img width="1812" height="3383" alt="localhost_3000_ (1)" src="https://github.com/user-attachments/assets/1d6a2a51-39db-48b8-9b91-fa55fca102ee" />

## Tech Stack

- Backend: Python, FastAPI
- Agent orchestration: LangGraph
- LLM provider: Groq via OpenAI-compatible HTTP calls
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

Set `GROQ_API_KEY` and `GROQ_CHAT_MODEL` in `backend/.env` before using LLM generation. The backend uses Groq's OpenAI-compatible API at `https://api.groq.com/openai/v1` by default.

Note: Chroma vector retrieval and session persistence are local, file-based services. LLM generation uses Groq, not Ollama.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

The frontend runs at `http://localhost:3000` by default.
