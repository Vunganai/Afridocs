import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  score: number | null | undefined;
  showLabel?: boolean;
}

export function ConfidenceBar({ score, showLabel = true }: ConfidenceBarProps) {
  if (score === null || score === undefined) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  const pct = Math.round(score * 100);
  const color =
    pct >= 95 ? "bg-green-500" :
    pct >= 80 ? "bg-yellow-400" :
    "bg-red-500";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      {showLabel && <span className="text-xs text-muted-foreground tabular-nums">{pct}%</span>}
    </div>
  );
}
