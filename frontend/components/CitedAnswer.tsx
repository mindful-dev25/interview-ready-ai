'use client';

import { useState } from "react";
import { splitCitations, type NumberedEvidence } from "@/lib/answers";

type CitedAnswerProps = {
  text: string;
  /** Evidence by id, with the number each item is shown under. */
  evidence: Map<string, NumberedEvidence>;
};

const numberBadge =
  "inline-flex min-w-[1.125rem] items-center justify-center rounded border px-1 text-[11px] font-semibold leading-4 tabular-nums";

/**
 * Answer text in which each citation marker is a numbered button. Clicking one
 * shows that evidence directly under the answer, so a claim can be checked in place.
 */
export default function CitedAnswer({ text, evidence }: CitedAnswerProps) {
  const [openId, setOpenId] = useState<string | null>(null);
  const segments = splitCitations(text, (id) => evidence.has(id));
  // The open citation can disappear from the text, for example after a revision.
  const open = openId && segments.some((segment) => segment.type === "citation" && segment.ids.includes(openId))
    ? evidence.get(openId)
    : undefined;

  return (
    <>
      <p className="mt-1 whitespace-pre-line text-[15px] leading-7 text-foreground">
        {segments.map((segment, position) => {
          if (segment.type === "text") return segment.text;
          // The word, its badges and the punctuation after them stay on one line.
          return (
            <span key={position} className="whitespace-nowrap">
              {segment.lead}
              {segment.ids.map((id) => {
                const cited = evidence.get(id);
                if (!cited) return null;
                const isOpen = open?.number === cited.number;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setOpenId(isOpen ? null : id)}
                    aria-expanded={isOpen}
                    aria-label={`Evidence ${cited.number}: ${cited.item.source ?? "source"}`}
                    title={cited.item.source}
                    className={`${numberBadge} ml-1 cursor-pointer align-text-top transition ${
                      isOpen
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-primary/40 bg-primary/10 text-primary hover:bg-primary/20"
                    }`}
                  >
                    {cited.number}
                  </button>
                );
              })}
              {segment.trail}
            </span>
          );
        })}
      </p>

      {open && (
        <div className="mt-3 rounded-md border border-primary/30 bg-primary/5 p-3 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2 font-medium">
              <span className={`${numberBadge} shrink-0 border-primary bg-primary text-primary-foreground`}>
                {open.number}
              </span>
              <span className="min-w-0">{open.item.source}</span>
            </div>
            <button
              type="button"
              onClick={() => setOpenId(null)}
              className="shrink-0 text-xs font-medium text-muted-foreground underline underline-offset-2"
            >
              Close
            </button>
          </div>
          <p className="mt-2 whitespace-pre-line leading-6 text-muted-foreground">
            {open.item.quote}
          </p>
          {open.item.relevance ? <p className="mt-2 text-xs text-muted-foreground">{open.item.relevance}</p> : null}
        </div>
      )}
    </>
  );
}
