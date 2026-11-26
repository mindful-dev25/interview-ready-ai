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
- `components/SignInGate.tsx` shows Google's sign-in button when the backend sets `GOOGLE_CLIENT_ID`, and `AccountStatus` in the same file shows who is signed in, with a sign-out button. `lib/google.ts` loads Google's button script. The page needs no Google setting of its own, because the backend returns the client ID from `GET /api/auth`. `lib/api.ts` sends the session cookie with every call (`credentials: "include"`), and `lib/types.ts` mirrors the backend response models.
- `components/` holds the UI pieces, built with React, TypeScript, and Tailwind CSS.
