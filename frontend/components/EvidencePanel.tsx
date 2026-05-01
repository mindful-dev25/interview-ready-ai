import type { EvidenceItem } from "@/lib/types";

type EvidencePanelProps = {
  items: EvidenceItem[];
};

export default function EvidencePanel({ items }: EvidencePanelProps) {
  return (
    <aside className="rounded-lg border border-border bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold">Evidence</h2>
      <div className="mt-4 flex flex-col gap-3">
        {items.map((item) => (
          <div key={`${item.source}-${item.quote}`} className="rounded-md border border-border p-3">
            <div className="text-sm font-medium">{item.source}</div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.quote}</p>
            <p className="mt-2 text-xs text-muted-foreground">{item.relevance}</p>
          </div>
        ))}
      </div>
    </aside>
  );
}
