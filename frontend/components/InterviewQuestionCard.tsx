import type { ReactNode } from "react";

type InterviewQuestionCardProps = {
  /** 1-based position of the question in the list. */
  number: number;
  question: string;
  /** The answer, already rendered. */
  answer: ReactNode;
  /** Small badges shown on the label row above the question. */
  status?: ReactNode;
  /** Notes and actions shown below the answer, at full width. */
  children?: ReactNode;
};

/**
 * A question and its answer. The badges sit on their own row so a long question
 * keeps the full card width, and the answer is set apart from the question.
 */
export default function InterviewQuestionCard({ number, question, answer, status, children }: InterviewQuestionCardProps) {
  return (
    <article className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Question {number}</span>
        {status ? <div className="flex flex-wrap gap-2">{status}</div> : null}
      </div>
      <h2 className="mt-2 text-base font-semibold leading-7 text-foreground">{question}</h2>

      <div className="mt-4 rounded-md border-l-4 border-primary/40 bg-slate-50 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Your answer</p>
        {answer}
      </div>
      {children}
    </article>
  );
}
