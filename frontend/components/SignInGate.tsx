'use client';

import { createContext, ReactNode, useContext, useEffect, useRef, useState } from "react";
import { LockKeyhole, LogOut } from "lucide-react";
import { authStatus, onLocked, signInWithGoogle, signOut } from "@/lib/api";
import { forgetGoogleAccount, renderGoogleButton } from "@/lib/google";

type GateState = "checking" | "open" | "locked";

type Account = { email: string; signOut: () => void };

const AccountContext = createContext<Account | null>(null);

/**
 * Asks people to sign in with Google when the backend sets GOOGLE_CLIENT_ID; otherwise shows the app straight away.
 * The backend verifies the ID token from Google's button and keeps the sign-in in a cookie. If that sign-in ends
 * later (it expired), the sign-in screen comes back over the page, and the work on the page stays as it was.
 */
export default function SignInGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GateState>("checking");
  const [wasOpen, setWasOpen] = useState(false);
  const [clientId, setClientId] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await authStatus();
        if (cancelled) return;
        setClientId(status.google_client_id);
        if (status.sign_in_required && !status.email) setState("locked");
        else open(status.email);
      } catch {
        // The server could not be reached. Show the app, whose own calls then explain the failure.
        open(null);
      }
    })();

    function open(signedInAs: string | null) {
      if (cancelled) return;
      setEmail(signedInAs);
      setState("open");
      setWasOpen(true);
    }

    const stopListening = onLocked(() => {
      setEmail(null);
      setError("Your sign-in has ended. Please sign in again.");
      setState("locked");
    });
    return () => {
      cancelled = true;
      stopListening();
    };
  }, []);

  // Draw Google's button whenever the sign-in screen shows.
  useEffect(() => {
    const parent = buttonRef.current;
    if (state !== "locked" || !parent) return;
    let cancelled = false;

    async function finishSignIn(credential: string) {
      setSubmitting(true);
      setError(null);
      try {
        const status = await signInWithGoogle(credential);
        setEmail(status.email);
        setState("open");
        setWasOpen(true);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Could not sign in with Google.");
      } finally {
        setSubmitting(false);
      }
    }

    (async () => {
      try {
        // The client ID comes from the server. Ask again if the first check could not reach it.
        const id = clientId ?? (await authStatus()).google_client_id;
        if (cancelled) return;
        if (!id) throw new Error("Google sign-in is not set up on the server.");
        await renderGoogleButton(parent, id, finishSignIn);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Could not load Google sign-in.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [state, clientId]);

  async function handleSignOut() {
    try {
      await signOut();
    } catch {
      // Reload anyway: if the cookie could not be cleared, the page shows you still signed in.
    }
    forgetGoogleAccount();
    // A fresh page, so nothing from this session stays on screen.
    window.location.reload();
  }

  if (state === "checking") return null;

  return (
    <AccountContext.Provider value={email ? { email, signOut: handleSignOut } : null}>
      {wasOpen ? children : null}
      {state === "locked" ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="sign-in-title"
            className="flex w-full max-w-sm flex-col gap-4 rounded-lg border border-border bg-white p-6 shadow-lg"
          >
            <div className="flex items-center gap-2">
              <LockKeyhole className="h-5 w-5 text-muted-foreground" aria-hidden />
              <h1 id="sign-in-title" className="text-lg font-semibold text-foreground">
                Interview Ready AI
              </h1>
            </div>
            <p className="text-sm text-muted-foreground">Sign in with your Google account to use the app.</p>
            <div ref={buttonRef} className="flex min-h-11 justify-center" aria-busy={submitting} />
            {submitting ? (
              <p role="status" className="text-sm text-muted-foreground">
                Signing in...
              </p>
            ) : null}
            {error ? (
              <p role="alert" className="text-sm text-red-700">
                {error}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </AccountContext.Provider>
  );
}

/** Who is signed in, with a button to sign out. Shows nothing when the app needs no sign-in. */
export function AccountStatus() {
  const account = useContext(AccountContext);
  if (!account) return null;
  return (
    <div className="flex min-w-0 items-center gap-3 text-sm text-muted-foreground">
      <span className="max-w-[16rem] truncate" title={account.email}>
        {account.email}
      </span>
      <button
        type="button"
        onClick={account.signOut}
        className="inline-flex min-h-9 shrink-0 items-center gap-1.5 rounded-md border border-border bg-white px-3 font-medium text-foreground transition hover:bg-slate-50"
      >
        <LogOut className="h-4 w-4" aria-hidden />
        Sign out
      </button>
    </div>
  );
}
