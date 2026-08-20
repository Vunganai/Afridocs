import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { DocumentListItem, PaginatedResponse } from "@/types";
import { AlertCircle } from "lucide-react";

export function ReviewQueuePage() {
  const navigate = useNavigate();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["workflow-queue"],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<DocumentListItem>>("/v1/workflow/queue");
      return data;
    },
    refetchInterval: 10_000,
  });

  return (
    <div className="container py-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Review Queue</h1>
        <p className="text-muted-foreground">Documents awaiting your approval</p>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
      ) : !data || data.items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-muted-foreground">No invoices pending review</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {data.items.map((doc) => (
            <Card
              key={doc.id}
              className="hover:bg-accent/50 cursor-pointer transition"
              onClick={() => navigate(`/review/${doc.id}`)}
            >
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{doc.supplierName || doc.originalFilename}</p>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                    {doc.invoiceNumber && <span>Invoice {doc.invoiceNumber}</span>}
                    {doc.invoiceDate && <span>• {formatDate(doc.invoiceDate)}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {doc.totalAmount && <span className="font-mono text-sm">{formatCurrency(doc.totalAmount, doc.currency)}</span>}
                  {doc.hasValidationWarnings && (
                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">Has warnings</span>
                  )}
                  <StatusBadge status={doc.status} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
