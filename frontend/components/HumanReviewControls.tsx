'use client';

import { useState } from "react";
import { Check, MessageSquare, X } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

type ReviewAction = "approve" | "edit" | "request_revision";

type ReviewResponse = {
  session_id: string;
  answer_id: string;
  human_status: string;
  message: string;
};

type Props = {
  sessionId?: string;
  answerId?: string;
  draftAnswer?: string;
};

export default function HumanReviewControls({
  sessionId = "sample-session",
  answerId = "a1",
  draftAnswer = "I solved a hard technical problem by breaking it into smaller pieces, validating each part, and collaborating with stakeholders to ensure alignment.",
}: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedAnswer, setEditedAnswer] = useState(draftAnswer);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string>("pending");

  async function submitReview(action: ReviewAction, editedAnswerValue?: string) {
    setStatusMessage("Saving review action...");
    setErrorMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          answer_id: answerId,
          action,
          edited_answer: editedAnswerValue,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Unable to submit review action.");
      }

      const payload: ReviewResponse = await response.json();
      setCurrentStatus(payload.human_status);
      setStatusMessage(payload.message);
      setIsEditing(false);
    } catch (error: unknown) {
      setStatusMessage(null);
      setErrorMessage(error instanceof Error ? error.message : "Review action failed.");
    }
  }

  function handleApprove() {
    submitReview("approve");
  }

  function handleRequestRevision() {
    submitReview("request_revision");
  }

  function handleSaveEdit() {
    if (!editedAnswer.trim()) {
      setErrorMessage("Edited answer cannot be empty.");
      return;
    }
    submitReview("edit", editedAnswer.trim());
  }

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Human Review</h2>
          <p className="text-sm text-muted-foreground">
            Review draft answers by approving them, editing final text, or requesting revision.
          </p>
          <p className="mt-2 text-sm">
            <span className="font-medium">Current status:</span> {currentStatus}
          </p>
          {statusMessage ? (
            <p className="mt-1 text-sm text-green-700">{statusMessage}</p>
          ) : null}
          {errorMessage ? (
            <p className="mt-1 text-sm text-red-700">{errorMessage}</p>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setIsEditing(!isEditing)}
            className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium"
          >
            <MessageSquare className="size-4" aria-hidden="true" />
            {isEditing ? "Cancel Edit" : "Edit"}
          </button>
          <button
            type="button"
            onClick={handleRequestRevision}
            className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium"
          >
            <X className="size-4" aria-hidden="true" />
            Request Revision
          </button>
          <button
            type="button"
            onClick={handleApprove}
            className="inline-flex min-h-10 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground"
          >
            <Check className="size-4" aria-hidden="true" />
            Approve
          </button>
        </div>
      </div>

      {isEditing ? (
        <div className="mt-4">
          <label className="mb-2 block text-sm font-medium text-foreground">Edit final answer</label>
          <textarea
            className="w-full rounded-md border border-border bg-background p-3 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
            rows={6}
            value={editedAnswer}
            onChange={(event) => setEditedAnswer(event.target.value)}
          />
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={handleSaveEdit}
              className="inline-flex min-h-10 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground"
            >
              Save Edit
            </button>
            <button
              type="button"
              onClick={() => {
                setEditedAnswer(draftAnswer);
                setIsEditing(false);
                setErrorMessage(null);
              }}
              className="inline-flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
