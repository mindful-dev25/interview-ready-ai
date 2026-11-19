'use client';

import { FormEvent, ReactNode, useEffect, useState } from "react";
import { LockKeyhole } from "lucide-react";
import { onLocked, passwordRequired, savedPassword, unlock } from "@/lib/api";

type GateState = "checking" | "open" | "locked";

/**
 * Asks for the app password when the backend sets APP_PASSWORD; otherwise shows the app straight away.
 * If the password stops working later (it was changed on the server), the form comes back over the page,
 * and the work on the page stays as it was.
 */
export default function PasswordGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GateState>("checking");
  const [wasOpen, setWasOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (!(await passwordRequired())) return open();
      } catch {
        // The server could not be reached. Show the app, whose own calls then explain the failure.
        return open();
      }
      try {
        const saved = savedPassword();
        if (saved) {
          await unlock(saved);
          return open();
        }
      } catch {
        // The saved password is no longer right: ask for it.
      }
      if (!cancelled) setState("locked");
    })();

    function open() {
      if (cancelled) return;
      setState("open");
      setWasOpen(true);
    }

    const stopListening = onLocked(() => {
      setError("Please enter the app password again.");
      setState("locked");
    });
    return () => {
      cancelled = true;
      stopListening();
    };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await unlock(password);
      setPassword("");
      setState("open");
      setWasOpen(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not check the password.");
    } finally {
      setSubmitting(false);
    }
  }

  if (state === "checking") return null;

  return (
    <>
      {wasOpen ? children : null}
      {state === "locked" ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <form
            onSubmit={submit}
            className="flex w-full max-w-sm flex-col gap-4 rounded-lg border border-border bg-white p-6 shadow-lg"
          >
            <div className="flex items-center gap-2">
              <LockKeyhole className="h-5 w-5 text-muted-foreground" aria-hidden />
              <h1 className="text-lg font-semibold text-foreground">Interview Ready AI</h1>
            </div>
            <label className="flex flex-col gap-2 text-sm text-muted-foreground">
              Enter the password to use the app.
              <input
                type="password"
                autoFocus
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="min-h-11 rounded-md border border-border px-3 text-foreground outline-none focus:ring-2 focus:ring-primary/40"
              />
            </label>
            {error ? (
              <p role="alert" className="text-sm text-red-700">
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={submitting || !password}
              className="min-h-11 rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Checking..." : "Continue"}
            </button>
          </form>
        </div>
      ) : null}
    </>
  );
}
