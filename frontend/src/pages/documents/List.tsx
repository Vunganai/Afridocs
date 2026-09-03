import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useToast } from "@/hooks/useToast";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { DocumentListItem, PaginatedResponse } from "@/types";
import { Upload, Eye, CheckCircle2, Trash2 } from "lucide-react";

export function DocumentListPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<DocumentListItem>>("/v1/documents");
      return data;
    },
    refetchInterval: (query) => {
      const hasPending = query.state.data?.items?.some(
        (d: any) => d.status === "pending" || d.status === "processing"
      );
      return hasPending ? 4000 : 20000;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/v1/documents/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-metrics"] });
      queryClient.invalidateQueries({ queryKey: ["workflow-queue"] });
      toast({ title: "Invoice deleted" });
    },
    onError: (err: Error) => {
      toast({ title: "Could not delete invoice", description: err.message, variant: "destructive" });
    },
  });

  return (
    <div className="container py-8 space-y-6 max-w-6xl">
      <div className="flex flex-wrap justify-between items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">Invoices</h1>
          <p className="text-muted-foreground">View and manage all uploaded and processed invoices</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => navigate("/review")}>
            <CheckCircle2 className="h-4 w-4 mr-2" />
            Review Queue
          </Button>
          <Button onClick={() => navigate("/upload")}>
            <Upload className="h-4 w-4 mr-2" />
            Upload
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading invoices...</div>
      ) : !data || data.items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">No invoices uploaded yet</p>
            <Button onClick={() => navigate("/upload")}>
              <Upload className="h-4 w-4 mr-2" />
              Upload your first invoice
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {data.items.map((doc) => {
            const raw = doc as (DocumentListItem & Record<string, any>);
            const supplierName =
              raw.supplierName ||
              raw.supplier_name ||
              raw.originalFilename ||
              raw.original_filename ||
              "Invoice";
            const invoiceNumber = raw.invoiceNumber || raw.invoice_number;
            const originalFilename = raw.originalFilename || raw.original_filename;
            const invoiceDate = raw.invoiceDate || raw.invoice_date;
            const totalAmount = raw.totalAmount || raw.total_amount;
            const currency = raw.currency || "ZAR";
            const status = raw.status;

            return (
              <Card
                key={raw.id}
                className="hover:bg-accent/40 cursor-pointer transition border"
                onClick={() => navigate(`/documents/${raw.id}`)}
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex-1 min-w-0 pr-4">
                    <p className="font-medium text-foreground truncate">{supplierName}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {invoiceNumber ? `Invoice ${invoiceNumber}` : originalFilename}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    {invoiceDate && (
                      <span className="text-xs text-muted-foreground hidden sm:inline">
                        {formatDate(invoiceDate)}
                      </span>
                    )}
                    {totalAmount && (
                      <span className="font-mono text-sm font-semibold">
                        {formatCurrency(totalAmount, currency)}
                      </span>
                    )}
                    <StatusBadge status={status as any} />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/documents/${raw.id}`);
                      }}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive hover:text-destructive gap-1"
                      disabled={deleteMutation.isPending}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm(`Delete invoice "${supplierName}"? This cannot be undone.`)) {
                          deleteMutation.mutate(raw.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
