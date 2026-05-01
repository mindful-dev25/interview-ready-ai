import { cn } from "@/lib/utils";

type GuardrailBadgeProps = {
  label: string;
  tone?: "neutral" | "success" | "warning";
};

const toneClasses = {
  neutral: "border-border bg-muted text-foreground",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
};

export default function GuardrailBadge({ label, tone = "neutral" }: GuardrailBadgeProps) {
  return (
    <span className={cn("inline-flex whitespace-nowrap rounded-md border px-2.5 py-1 text-xs font-medium", toneClasses[tone])}>
      {label}
    </span>
  );
}
