import type { EvidenceItem, HumanReviewStatus, InterviewAnswer } from "@/lib/types";

export type ReviewStatus = HumanReviewStatus;
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

/**
 * Distinct guardrail findings for an answer: an empty list means the checks
 * passed, and null means the answer has not been checked (for example after a revision).
 */
export function guardrailNotes(answer: InterviewAnswer): string[] | null {
  const truthfulness = answer.truthfulness_guardrail;
  const citation = answer.citation_guardrail;
  if (!truthfulness?.summary && !citation?.summary) return null;

  const notes = [
    ...(truthfulness?.claims ?? []).map((claim) => claim.explanation),
    ...(citation?.weak_citation_notes ?? []),
  ].filter((note): note is string => Boolean(note));
  return [...new Set(notes)];
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

/** An evidence item with the number it is shown under, both in answers and in the Evidence panel. */
export type NumberedEvidence = { number: number; item: EvidenceItem };

/** Number the evidence items 1, 2, 3... in panel order, keyed by id, so answers can refer to them. */
export function indexEvidence(items: EvidenceItem[]): Map<string, NumberedEvidence> {
  const index = new Map<string, NumberedEvidence>();
  items.forEach((item, position) => {
    if (item.id) index.set(item.id, { number: position + 1, item });
  });
  return index;
}

/**
 * A run of answer text, or a group of adjacent citations. A citation group carries
 * the word before it (`lead`) and any punctuation right after it (`trail`), so the
 * three can be kept on one line.
 */
export type AnswerSegment =
  | { type: "text"; text: string }
  | { type: "citation"; ids: string[]; lead: string; trail: string };

/** A bracketed marker, which may list several ids: `[a]`, `[a, b]`. */
const CITATION_MARKER = /\[([^\[\]]+)\]/g;
/** The shape of the backend's evidence ids, used to hide citations to evidence that is not shown. */
const EVIDENCE_ID = /^evidence[-_]\w+$/i;
const LAST_WORD = /\S+$/;
const LEADING_PUNCTUATION = /^[.,;:!?)]+/;

/** The known ids a marker cites, or null when the marker is ordinary bracketed text. */
function markerIds(inner: string, isKnownEvidence: (id: string) => boolean): string[] | null {
  const ids = inner.split(/[,;]/).map((id) => id.trim());
  if (!ids.every((id) => isKnownEvidence(id) || EVIDENCE_ID.test(id))) return null;
  return ids.filter(isKnownEvidence);
}

/**
 * Split answer text at citation markers such as `[evidence-1a2b]` or
 * `[evidence-1a2b, evidence-3c4d]`. Adjacent markers form one group. Markers that
 * cite evidence not in the list are dropped; other bracketed text is left as it is.
 */
export function splitCitations(text: string, isKnownEvidence: (id: string) => boolean): AnswerSegment[] {
  // Alternating text and id groups: texts[k] comes before groups[k], texts[k + 1] after it.
  const texts: string[] = [];
  const groups: string[][] = [];
  let textStart = 0;
  for (const match of text.matchAll(CITATION_MARKER)) {
    const ids = markerIds(match[1], isKnownEvidence);
    if (ids === null) continue;
    const between = text.slice(textStart, match.index);
    if (groups.length > 0 && !between.trim()) {
      groups[groups.length - 1].push(...ids);
    } else {
      texts.push(between);
      groups.push(ids);
    }
    textStart = match.index + match[0].length;
  }
  texts.push(text.slice(textStart));

  const segments: AnswerSegment[] = [];
  const pushText = (value: string) => {
    if (value) segments.push({ type: "text", text: value });
  };
  groups.forEach((group, k) => {
    let before = texts[k].trimEnd();
    const ids = [...new Set(group)];
    if (ids.length === 0) {
      pushText(before);
      return;
    }
    const lead = before.match(LAST_WORD)?.[0] ?? "";
    before = before.slice(0, before.length - lead.length);
    const trail = texts[k + 1].match(LEADING_PUNCTUATION)?.[0] ?? "";
    texts[k + 1] = texts[k + 1].slice(trail.length);
    pushText(before);
    segments.push({ type: "citation", ids, lead, trail });
  });
  pushText(texts[texts.length - 1]);
  return segments;
}

export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
