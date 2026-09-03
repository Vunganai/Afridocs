import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { DocumentListItem, PaginatedResponse } from "@/types";
import { AlertCircle, CheckCircle, FileCheck, RotateCw } from "lucide-react";

export function ReviewQueuePage() {
  const navigate = useNavigate();
  const [selectedTab, setSelectedTab] = useState<"all" | "review_required" | "extracted">("all");

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["workflow-queue", selectedTab],
    queryFn: async () => {
      const url =
        selectedTab === "all"
          ? "/v1/workflow/queue"
          : `/v1/workflow/queue?status=${selectedTab}`;
      const { data } = await apiClient.get<PaginatedResponse<DocumentListItem>>(url);
      return data;
    },
    refetchInterval: 10_000,
  });

  return (
    <div className="container py-8 space-y-6 max-w-6xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Review Queue</h1>
          <p className="text-muted-foreground">Invoices awaiting human review and sign-off</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RotateCw className={`h-4 w-4 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Tabs / Filters */}
      <div className="flex border-b space-x-4">
        <button
          onClick={() => setSelectedTab("all")}
          className={`pb-3 text-sm font-medium border-b-2 transition ${
            selectedTab === "all"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          All Items ({data?.total ?? 0})
        </button>
        <button
          onClick={() => setSelectedTab("review_required")}
          className={`pb-3 text-sm font-medium border-b-2 transition flex items-center gap-1.5 ${
            selectedTab === "review_required"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <AlertCircle className="h-3.5 w-3.5 text-yellow-600" />
          Needs Review
        </button>
        <button
          onClick={() => setSelectedTab("extracted")}
          className={`pb-3 text-sm font-medium border-b-2 transition flex items-center gap-1.5 ${
            selectedTab === "extracted"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileCheck className="h-3.5 w-3.5 text-blue-600" />
          Ready for Sign-off
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading queue...</div>
      ) : !data || data.items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle className="h-10 w-10 mx-auto mb-3 text-green-600/80" />
            <p className="font-semibold text-foreground">Queue is clear</p>
            <p className="text-sm text-muted-foreground mt-1">
              {selectedTab === "all"
                ? "No invoices are currently pending review or approval."
                : `No invoices found with status '${selectedTab.replace("_", " ")}'.`}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {data.items.map((item) => {
            const raw = item as (DocumentListItem & Record<string, any>);
            const supplierName =
              raw.supplierName ||
              raw.supplier_name ||
              raw.originalFilename ||
              raw.original_filename ||
              "Invoice";
            const invoiceNumber = raw.invoiceNumber || raw.invoice_number;
            const invoiceDate = raw.invoiceDate || raw.invoice_date;
            const totalAmount = raw.totalAmount || raw.total_amount;
            const currency = raw.currency || "ZAR";
            const hasWarnings = raw.hasValidationWarnings ?? raw.has_validation_warnings ?? false;
            const status = raw.status;

            return (
              <Card
                key={raw.id}
                className="hover:bg-accent/40 cursor-pointer transition border"
                onClick={() => navigate(`/review/${raw.id}`)}
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex-1 min-w-0 pr-4">
                    <p className="font-medium text-foreground truncate">{supplierName}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                      {invoiceNumber && <span>Invoice {invoiceNumber}</span>}
                      {invoiceDate && <span>• {formatDate(invoiceDate)}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    {totalAmount && (
                      <span className="font-mono text-sm font-semibold">
                        {formatCurrency(totalAmount, currency)}
                      </span>
                    )}
                    {hasWarnings && (
                      <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded font-medium">
                        Has warnings
                      </span>
                    )}
                    <StatusBadge status={status as any} />
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
