import type { EvidenceItem, InterviewAnswer } from "@/lib/types";

export type ReviewStatus = NonNullable<InterviewAnswer["human_status"]>;
export type ReviewCounts = Record<ReviewStatus, number>;

const statusLabels: Record<ReviewStatus, string> = {
  pending: "Needs review",
  needs_revision: "Needs revision",
  approved: "Approved",
  edited: "Edited",
};

const statusTones: Record<ReviewStatus, "neutral" | "success" | "warning"> = {
  pending: "warning",
  needs_revision: "warning",
  approved: "success",
  edited: "success",
};

export function reviewStatus(answer: InterviewAnswer): ReviewStatus {
  return answer.human_status ?? "pending";
}

export function statusLabel(answer: InterviewAnswer): string {
  return statusLabels[reviewStatus(answer)];
}

export function statusTone(answer: InterviewAnswer) {
  return statusTones[reviewStatus(answer)];
}

/** The reviewer's final answer if there is one, otherwise the AI draft. */
export function answerText(answer: InterviewAnswer): string {
  return answer.final_answer?.trim() ? answer.final_answer : answer.draft_answer;
}

export function isReviewed(answer: InterviewAnswer): boolean {
  return answer.human_status === "approved" || answer.human_status === "edited";
}

export function countReviews(answers: InterviewAnswer[]): ReviewCounts {
  const counts: ReviewCounts = { pending: 0, approved: 0, edited: 0, needs_revision: 0 };
  answers.forEach((answer) => {
    counts[reviewStatus(answer)] += 1;
  });
  return counts;
}

/** Evidence cited across all answers, de-duplicated by id/quote and source. */
export function collectEvidence(answers: InterviewAnswer[]): EvidenceItem[] {
  const seen = new Set<string>();
  const items: EvidenceItem[] = [];
  answers.forEach((answer) => {
    answer.evidence_used?.forEach((item) => {
      const key = `${item.id ?? item.quote}-${item.source ?? item.source_type}`;
      if (seen.has(key)) return;
      seen.add(key);
      items.push({
        id: item.id,
        source: item.source ?? item.source_type ?? "Evidence",
        quote: item.quote,
        relevance: item.relevance ?? "",
      });
    });
  });
  return items;
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
