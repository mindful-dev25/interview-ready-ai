# Interview Ready AI Frontend

Next.js frontend for uploading resume context, submitting a job URL or pasted job description, reviewing generated interview answers, and generating a final prep report.

## Setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

The app runs at `http://localhost:3000`.

## Structure

- `app/page.tsx` composes the page.
- `lib/hooks/` holds the session state and API actions (`useInterviewSession`) and resume input (`useResumeInput`).
- `components/PasswordGate.tsx` asks for the app password when the backend sets `APP_PASSWORD`, and `lib/api.ts` sends it with every call; `lib/types.ts` mirrors the backend response models.
- `components/` holds the UI pieces, built with React, TypeScript, and Tailwind CSS.
