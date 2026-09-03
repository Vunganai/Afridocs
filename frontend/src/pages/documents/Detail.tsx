import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { useToast } from "@/hooks/useToast";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/utils";
import type { DocumentDetail } from "@/types";
import { ArrowLeft, AlertTriangle, Copy, Play, CheckCircle2, Trash2 } from "lucide-react";

export function DocumentDetailPage() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    data: doc,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["document", documentId],
    queryFn: async () => {
      const { data } = await apiClient.get<DocumentDetail>(`/v1/documents/${documentId}`);
      return data;
    },
    refetchInterval: (query) => {
      const st = query.state.data?.status;
      return st === "pending" || st === "processing" ? 3000 : false;
    },
  });

  const processMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/v1/documents/${documentId}/process?sync=true`);
    },
    onSuccess: () => {
      toast({
        title: "Processing initiated",
        description: "Invoice extraction pipeline has started.",
      });
      refetch();
    },
    onError: (err: Error) => {
      toast({
        title: "Processing error",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await apiClient.delete(`/v1/documents/${documentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-metrics"] });
      queryClient.invalidateQueries({ queryKey: ["workflow-queue"] });
      toast({ title: "Invoice deleted" });
      navigate("/documents");
    },
    onError: (err: Error) => {
      toast({ title: "Could not delete invoice", description: err.message, variant: "destructive" });
    },
  });

  if (isLoading) {
    return (
      <div className="container py-8">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="container py-8 text-center">
        <p className="text-muted-foreground">Document not found.</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate("/documents")}>
          Back to documents
        </Button>
      </div>
    );
  }

  const rawDoc = doc as (DocumentDetail & Record<string, any>);
  const supplierName = rawDoc.supplierName || rawDoc.supplier_name || rawDoc.originalFilename || rawDoc.original_filename;
  const invoiceNumber = rawDoc.invoiceNumber || rawDoc.invoice_number;
  const status = rawDoc.status || "pending";
  const extractedFields = rawDoc.extractedFields || rawDoc.extracted_fields || [];
  const isDuplicate = rawDoc.isDuplicate ?? rawDoc.is_duplicate ?? false;
  const totalAmount = rawDoc.totalAmount || rawDoc.total_amount;
  const vatAmount = rawDoc.vatAmount || rawDoc.vat_amount;
  const invoiceDate = rawDoc.invoiceDate || rawDoc.invoice_date;
  const dueDate = rawDoc.dueDate || rawDoc.due_date;
  const currency = rawDoc.currency || "ZAR";
  const hasValidationWarnings = rawDoc.hasValidationWarnings ?? rawDoc.has_validation_warnings ?? false;
  const processingError = rawDoc.processingError || rawDoc.processing_error;
  const originalFilename = rawDoc.originalFilename || rawDoc.original_filename;
  const mimeType = rawDoc.mimeType || rawDoc.mime_type;
  const fileSizeBytes = rawDoc.fileSizeBytes || rawDoc.file_size_bytes || 0;
  const createdAt = rawDoc.createdAt || rawDoc.created_at;
  const classificationConfidence = rawDoc.classificationConfidence ?? rawDoc.classification_confidence ?? null;
  const ingestionChannel = rawDoc.ingestionChannel || rawDoc.ingestion_channel || "upload";

  return (
    <div className="container py-8 max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Button variant="ghost" size="sm" onClick={() => navigate("/documents")} className="mb-2 -ml-2">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <h1 className="text-2xl font-bold">{supplierName}</h1>
          <div className="flex items-center gap-2 mt-1">
            {invoiceNumber && (
              <span className="text-sm text-muted-foreground">Invoice {invoiceNumber}</span>
            )}
            <StatusBadge status={status as any} />
            {isDuplicate && (
              <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded flex items-center gap-1">
                <Copy className="h-3 w-3" /> Duplicate
              </span>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {(status === "pending" || status === "processing" || status === "failed") && (
            <Button
              variant="outline"
              onClick={() => processMutation.mutate()}
              disabled={processMutation.isPending}
            >
              <Play className="h-4 w-4 mr-2" />
              {processMutation.isPending ? "Processing..." : "Process Invoice"}
            </Button>
          )}

          {(status === "review_required" || status === "extracted") && (
            <Button onClick={() => navigate(`/review/${rawDoc.id}`)}>
              <CheckCircle2 className="h-4 w-4 mr-2" />
              Review &amp; Approve
            </Button>
          )}
          <Button
            variant="outline"
            className="text-destructive hover:text-destructive"
            disabled={deleteMutation.isPending}
            onClick={() => {
              if (window.confirm("Delete this invoice? This cannot be undone.")) {
                deleteMutation.mutate();
              }
            }}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            {deleteMutation.isPending ? "Deleting..." : "Delete"}
          </Button>
        </div>
      </div>

      {/* Pending / Processing Info Banner */}
      {(status === "pending" || status === "processing") && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-4 w-4 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
            <div>
              <p className="font-medium text-blue-900 text-sm">Processing in progress</p>
              <p className="text-xs text-blue-700">
                The AI extraction worker is analyzing this invoice. Extracted fields will appear automatically once done.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Key figures */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Total Amount</p>
            <p className="text-xl font-bold">{formatCurrency(totalAmount, currency)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">VAT</p>
            <p className="text-xl font-bold">{formatCurrency(vatAmount, currency)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Invoice Date</p>
            <p className="text-xl font-bold">{formatDate(invoiceDate)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Due Date</p>
            <p className="text-xl font-bold">{formatDate(dueDate)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Warnings */}
      {hasValidationWarnings && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>This document has validation warnings. Review the extracted fields below.</span>
        </div>
      )}

      {/* Processing error */}
      {processingError && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded text-sm text-destructive">
          Processing error: {processingError}
        </div>
      )}

      {/* Extracted Fields */}
      {extractedFields.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-base">Extracted Fields</CardTitle>
            {(status === "review_required" || status === "extracted") && (
              <Button size="sm" variant="ghost" onClick={() => navigate(`/review/${rawDoc.id}`)}>
                Edit in Review Mode &rarr;
              </Button>
            )}
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {extractedFields.map((f: any) => {
                const key = f.fieldName || f.field_name || "";
                const val = f.effectiveValue || f.effective_value || f.fieldValue || f.field_value || "—";
                const wasCorrected = f.wasCorrected ?? f.was_corrected ?? false;
                const validationStatus = f.validationStatus || f.validation_status;
                const validationMessage = f.validationMessage || f.validation_message;
                const confidence = f.confidenceScore ?? f.confidence_score;

                return (
                  <div key={f.id || key} className="flex items-center justify-between py-3 gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium capitalize">
                        {key.replace(/_/g, " ")}
                      </p>
                      <p className="text-sm text-foreground truncate">
                        {val}
                        {wasCorrected && (
                          <span className="ml-2 text-xs text-green-600">(corrected)</span>
                        )}
                      </p>
                      {validationMessage && validationStatus !== "valid" && (
                        <p className="text-xs text-muted-foreground mt-0.5">{validationMessage}</p>
                      )}
                    </div>
                    <div className="shrink-0">
                      <ConfidenceBar score={confidence} showLabel />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* File metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">File Details</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-muted-foreground">Filename</p>
            <p className="font-medium truncate">{originalFilename}</p>
          </div>
          <div>
            <p className="text-muted-foreground">MIME type</p>
            <p className="font-medium">{mimeType}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Size</p>
            <p className="font-medium">{(fileSizeBytes / 1024).toFixed(1)} KB</p>
          </div>
          <div>
            <p className="text-muted-foreground">Uploaded</p>
            <p className="font-medium">{formatDateTime(createdAt)}</p>
          </div>
          {classificationConfidence !== null && (
            <div>
              <p className="text-muted-foreground">Classification confidence</p>
              <ConfidenceBar score={classificationConfidence} showLabel />
            </div>
          )}
          <div>
            <p className="text-muted-foreground">Channel</p>
            <p className="font-medium capitalize">{ingestionChannel}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
