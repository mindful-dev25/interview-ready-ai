# Interview Ready AI

Interview Ready AI is a Claude-backed, agentic RAG application for interview preparation. You give it your resume and a job posting. It writes interview questions for that role and drafts an answer to each one from your own experience, citing the evidence it used. You review every answer, and the approved answers become a final prep report.

## Demo

From a resume and a job posting to reviewed answers and the final report:

![Demo: analyzing a resume against a job posting, reviewing the cited answers, and generating the final report](docs/demo.gif)

## How It Works

### 1. Add your resume and the job

Upload a PDF or text resume, or paste its text. For the job, paste the posting URL, or paste the description itself for sites that block automated access. While the analysis runs, a progress bar shows each step: reading the resume and the job, pulling company details out of the posting, writing the questions, then drafting answers. If the job page can't be read (blocked, or behind a login), the analysis stops right away and asks you to paste the description instead.

You get 10 questions: two standard openers ("Tell me about yourself", "Why are you interested in this role?"), seven questions tailored to your resume and the job, and "What questions do you have for us?" to close.

![Resume and job inputs, with the analysis progress bar](docs/screenshots/01-analyze.png)

### 2. Review each answer

Each question gets a first-person answer in plain English. The numbered badges are citations: click one to read the resume or job text it comes from, right under the answer. Guardrail notes flag claims the evidence doesn't back up. For each answer you can **Approve** it, **Edit** it yourself, or **Request revision** with a note, and Claude rewrites it. **Approve all** approves every answer still waiting for review. The review summary and evidence list stay beside the answers as you scroll.

![An answer with an opened citation, next to the review summary and evidence list](docs/screenshots/02-review.png)

### 3. Generate the final report

Once every answer is approved or edited, **Generate final report** builds a prep report below the answers: a company and role overview, your background, every question with its full approved answer (word for word, not summarized), coaching tips, questions to ask, and risks to prepare for. If you change an answer afterwards, the next report is rebuilt from the updated answers.

![The final report](docs/screenshots/03-final-report.png)

## Tech Stack

- Backend: Python, FastAPI
- Orchestration: an async analysis pipeline (scrape, parse, research, index, generate, draft, check)
- LLM provider: Claude via the Anthropic Python SDK
- Retrieval: local keyword index stored as JSON files
- Frontend: Next.js, React, TypeScript
- Styling: Tailwind CSS, with lucide-react icons
- Report rendering: react-markdown

## Project Structure

```text
backend/   FastAPI API, analysis pipeline, RAG and guardrail services, and storage adapters
frontend/  Next.js app shell and interview-prep UI components
docs/      Demo recording and README screenshots
Dockerfile, start.sh   One-container image for deployment (see Deployment)
```

See [backend/README.md](backend/README.md) for the API endpoints and [frontend/README.md](frontend/README.md) for the UI code layout.

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

The frontend runs at `http://localhost:3000` by default. It calls the API at `NEXT_PUBLIC_API_BASE_URL` (`http://localhost:8000/api` by default), and the backend only accepts requests from the origins in `ALLOWED_ORIGINS`, so update that if you run the frontend on another port.

### Password protection (optional)

Set `APP_PASSWORD` in `backend/.env` to make the app ask for a password before it can be used. Every API call except the health check then needs it, so nobody can run analyses (and spend your Claude credits) or read sessions without it. The browser remembers the password after the first sign-in. Leave `APP_PASSWORD` empty and the app is open to everyone, which is the default for local use.

It is one shared password for the whole app, not user accounts, so use a long one and only serve it over HTTPS.

### Tests

```bash
cd backend
uv run pytest
```

The tests run offline: web fetches and Claude calls are replaced by fakes. For the frontend, `npx tsc --noEmit` type-checks the code.

## Deployment

### One container

The repository includes a `Dockerfile` that builds both halves into one image. Inside the container, Next.js serves the site on port 10000 and forwards every `/api` request to FastAPI, which listens only inside the container. The browser sees a single site, so there is no CORS setup and no API URL to configure. Sessions and the retrieval index are written to `/data`, so mount a persistent volume there.

To try the image locally: `docker build -t interview-ready-ai .` then `docker run -p 10000:10000 -e ANTHROPIC_API_KEY=... -v irai-data:/data interview-ready-ai`, and open `http://localhost:10000`.

### Northflank (free)

Northflank's free Sandbox runs the image with a persistent volume and keeps it running (no sleeping). It is meant for demos and testing rather than production. Northflank may ask for a card to verify your account; the Sandbox itself is free. Button names below may differ slightly in the dashboard.

1. Push the repository to GitHub, and sign up at [northflank.com](https://northflank.com) (signing up with GitHub links your repositories in one step).
2. Create a project. The free Sandbox allows 2 projects and 2 services.
3. In the project, choose **Create new > Service**, then **Combined service** (it builds and deploys from a repository).
   - **Repository:** this repository, branch `main`.
   - **Build type:** Dockerfile, with Dockerfile path `/Dockerfile` and build context `/`.
   - **Compute plan:** the largest the Sandbox offers, at least 0.2 vCPU and 512 MB (Node and Python run side by side).
   - **Ports:** Northflank reads port 10000 from the Dockerfile. Check that it is set to HTTP and **Public**.
4. Before the first deploy finishes, open the service's **Environment** page and add the runtime variables `ANTHROPIC_API_KEY` and, optionally, `APP_PASSWORD`.
5. On the **Volumes** page, add a volume (Single Read/Write, the smallest size) with container mount path `/data`. Without it, sessions are lost on every restart and deploy. A volume can only grow later, never shrink.
6. On the **Health checks** page, add a readiness check: HTTP, path `/api/health`, port 10000.
7. Open the public URL (it ends in `.code.run`) from the service's header once the deploy is running.

New commits on `main` rebuild and redeploy automatically while CI is turned on for the service. Change `APP_PASSWORD` on the **Environment** page; the service restarts with the new value.

### Separate frontend and backend

The two halves can also be deployed on their own hosts:

- **Backend:** any host that runs a long-lived Python process. An analysis can stream for a few minutes, so avoid serverless functions with short time limits. Sessions and the retrieval index are files, so attach a persistent disk and point `SESSION_STORE_PATH` and `CHROMA_PERSIST_DIR` at it; without one, sessions are lost on every restart. Install with `uv sync --frozen` and start with `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Frontend:** any host that runs `npm run build` then `npm start`. Have the browser call the backend directly as below, rather than forwarding `/api` through the frontend host, whose proxy may cut off a long analysis.

| Where | Setting | Value |
| --- | --- | --- |
| Backend | `ANTHROPIC_API_KEY` | Your Claude API key |
| Backend | `ALLOWED_ORIGINS` | The frontend's URL, for example `https://interview-ready.example.com` |
| Backend | `APP_PASSWORD` | A long shared password, or empty for open access |
| Frontend | `NEXT_PUBLIC_API_BASE_URL` | The backend's URL plus `/api`. It is built into the page, so rebuild the frontend after changing it |

Set these in the host's environment settings rather than committing a `.env` file.
