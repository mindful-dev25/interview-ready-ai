import type { ReactNode } from "react";

type InterviewQuestionCardProps = {
  question: string;
  answer: string;
  children?: ReactNode;
};

export default function InterviewQuestionCard({ question, answer, children }: InterviewQuestionCardProps) {
  return (
    <article className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <h2 className="text-lg font-semibold leading-7">{question}</h2>
        {children}
      </div>
      <p className="mt-4 text-sm leading-6 text-muted-foreground">{answer}</p>
    </article>
  );
}
