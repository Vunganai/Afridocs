import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/types";

const STATUS_CONFIG: Record<DocumentStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" }> = {
  pending:          { label: "Pending",        variant: "secondary" },
  processing:       { label: "Processing",     variant: "info" },
  extracted:        { label: "Extracted",      variant: "info" },
  review_required:  { label: "Review Required", variant: "warning" },
  approved:         { label: "Approved",       variant: "success" },
  rejected:         { label: "Rejected",       variant: "destructive" },
  duplicate:        { label: "Duplicate",      variant: "destructive" },
  failed:           { label: "Failed",         variant: "destructive" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const config = STATUS_CONFIG[status] ?? { label: status, variant: "outline" as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
