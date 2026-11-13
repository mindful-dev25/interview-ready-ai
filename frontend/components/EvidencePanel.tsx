'use client';

import { useState } from "react";
import type { EvidenceItem } from "@/lib/types";

type EvidencePanelProps = {
  items: EvidenceItem[];
};

// Quotes longer than this start collapsed, so the panel can be scanned.
const LONG_QUOTE_CHARS = 280;

export default function EvidencePanel({ items }: EvidencePanelProps) {
  return (
    <aside className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Evidence</h2>
      {items.length > 0 && (
        <p className="text-sm text-muted-foreground">
          The numbers match the citations in the answers. Click a number in an answer to read its evidence there.
        </p>
      )}
      <div className="mt-4 flex flex-col gap-3">
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No evidence retrieved yet. Evidence will appear here once resume and job context are indexed.
          </p>
        ) : (
          items.map((item, position) => (
            <EvidenceCard key={item.id ?? `${item.source}-${item.quote}`} item={item} number={position + 1} />
          ))
        )}
      </div>
    </aside>
  );
}

function EvidenceCard({ item, number }: { item: EvidenceItem; number: number }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = item.quote.length > LONG_QUOTE_CHARS;

  return (
    <div className="rounded-md border border-border p-3">
      <div className="flex items-start gap-2 text-sm font-medium">
        <span className="inline-flex min-w-5 shrink-0 items-center justify-center rounded border border-primary/40 bg-primary/10 px-1 text-xs font-semibold leading-5 tabular-nums text-primary">
          {number}
        </span>
        <span className="min-w-0">{item.source}</span>
      </div>
      <p
        className={`mt-2 whitespace-pre-line text-sm leading-6 text-muted-foreground ${
          isLong && !expanded ? "line-clamp-4" : ""
        }`}
      >
        {item.quote}
      </p>
      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          className="mt-1 text-xs font-medium text-primary underline underline-offset-2"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
      {item.relevance ? <p className="mt-2 text-xs text-muted-foreground">{item.relevance}</p> : null}
    </div>
  );
}
