import CitedAnswer from "@/components/CitedAnswer";
import GuardrailBadge from "@/components/GuardrailBadge";
import InterviewQuestionCard from "@/components/InterviewQuestionCard";
import { answerText, guardrailNotes, statusLabel, statusTone, type NumberedEvidence } from "@/lib/answers";
import type { InterviewAnswer } from "@/lib/types";

type AnswerReviewCardProps = {
  answer: InterviewAnswer;
  /** 1-based position of the question in the list. */
  number: number;
  /** All evidence by id, numbered as in the Evidence panel. */
  evidence: Map<string, NumberedEvidence>;
  isRevising: boolean;
  revisionNotes: string;
  revisionLoading: boolean;
  reviewError: string | null;
  onApprove: () => void;
  onEdit: (editedAnswer: string) => void;
  onToggleRevision: () => void;
  onRevisionNotesChange: (notes: string) => void;
  onSubmitRevision: () => void;
};

const actionButton = "whitespace-nowrap rounded-md border border-border px-3 py-2 text-sm font-medium";

export default function AnswerReviewCard({
  answer,
  number,
  evidence,
  isRevising,
  revisionNotes,
  revisionLoading,
  reviewError,
  onApprove,
  onEdit,
  onToggleRevision,
  onRevisionNotesChange,
  onSubmitRevision,
}: AnswerReviewCardProps) {
  const text = answerText(answer);
  const notes = guardrailNotes(answer);

  function promptForEdit() {
    const edited = prompt("Edit final answer:", text);
    if (edited !== null) {
      onEdit(edited);
    }
  }

  return (
    <InterviewQuestionCard
      number={number}
      question={answer.question.question}
      answer={<CitedAnswer text={text} evidence={evidence} />}
      status={
        <>
          {notes?.length === 0 && <GuardrailBadge label="Guardrails passed" tone="success" />}
          <GuardrailBadge label={statusLabel(answer)} tone={statusTone(answer)} />
        </>
      }
    >
      {notes && notes.length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer font-medium text-amber-800">
            {notes.length} guardrail {notes.length === 1 ? "note" : "notes"}
          </summary>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-muted-foreground">
            {notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="mt-4 flex flex-wrap justify-end gap-2 border-t border-border pt-4">
        <button type="button" onClick={onApprove} className={`${actionButton} bg-emerald-50 text-emerald-800`}>
          Approve
        </button>
        <button type="button" onClick={onToggleRevision} className={`${actionButton} bg-amber-50 text-amber-800`}>
          {isRevising ? "Cancel revision" : "Request revision"}
        </button>
        <button type="button" onClick={promptForEdit} className={`${actionButton} bg-slate-50 text-foreground`}>
          Edit
        </button>
      </div>

      {isRevising && (
        <div className="mt-3">
          <textarea
            className="w-full rounded-md border border-border bg-background p-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
            rows={3}
            placeholder="Describe what needs to change (e.g. 'Add a specific metric', 'Make it more concise')..."
            value={revisionNotes}
            onChange={(e) => onRevisionNotesChange(e.target.value)}
          />
          {reviewError && <p className="mt-1 text-sm text-red-700">{reviewError}</p>}
          <div className="mt-2 flex justify-end">
            <button
              type="button"
              disabled={revisionLoading}
              onClick={onSubmitRevision}
              className="whitespace-nowrap rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
            >
              {revisionLoading ? "Revising..." : "Submit revision"}
            </button>
          </div>
        </div>
      )}
    </InterviewQuestionCard>
  );
}
