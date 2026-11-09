import GuardrailBadge from "@/components/GuardrailBadge";
import InterviewQuestionCard from "@/components/InterviewQuestionCard";
import { answerText, statusLabel, statusTone } from "@/lib/answers";
import type { InterviewAnswer } from "@/lib/types";

type AnswerReviewCardProps = {
  answer: InterviewAnswer;
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

export default function AnswerReviewCard({
  answer,
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

  function promptForEdit() {
    const edited = prompt("Edit final answer:", text);
    if (edited !== null) {
      onEdit(edited);
    }
  }

  return (
    <InterviewQuestionCard question={answer.question.question} answer={text}>
      <div className="flex flex-col items-end gap-2 w-full">
        <GuardrailBadge label={statusLabel(answer)} tone={statusTone(answer)} />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onApprove}
            className="rounded-md border border-border bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={onToggleRevision}
            className="rounded-md border border-border bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800"
          >
            {isRevising ? "Cancel" : "Request revision"}
          </button>
          <button
            type="button"
            onClick={promptForEdit}
            className="rounded-md border border-border bg-slate-50 px-3 py-2 text-sm font-medium text-foreground"
          >
            Edit
          </button>
        </div>
        {isRevising && (
          <div className="mt-2 w-full">
            <textarea
              className="w-full rounded-md border border-border bg-background p-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
              rows={3}
              placeholder="Describe what needs to change (e.g. 'Add a specific metric', 'Make it more concise')..."
              value={revisionNotes}
              onChange={(e) => onRevisionNotesChange(e.target.value)}
            />
            {reviewError && <p className="mt-1 text-sm text-red-700">{reviewError}</p>}
            <button
              type="button"
              disabled={revisionLoading}
              onClick={onSubmitRevision}
              className="mt-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
            >
              {revisionLoading ? "Revising..." : "Submit revision"}
            </button>
          </div>
        )}
      </div>
    </InterviewQuestionCard>
  );
}
