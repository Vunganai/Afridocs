import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { useToast } from "@/hooks/useToast";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { DocumentDetail } from "@/types";
import {
  Check,
  X,
  Save,
  ArrowLeft,
  FileText,
  AlertTriangle,
  Play,
  RotateCcw,
  Trash2,
} from "lucide-react";

export function ReviewDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { profile } = useAuthStore();

  const [comment, setComment] = useState("");
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [originalValues, setOriginalValues] = useState<Record<string, string>>({});

  // ── 1. Fetch Document Detail ───────────────────────────────────────────
  const {
    data: doc,
    isLoading,
    isError,
    error,
    refetch: refetchDoc,
  } = useQuery({
    queryKey: ["document", documentId],
    queryFn: async () => {
      const { data } = await apiClient.get<DocumentDetail>(`/v1/documents/${documentId}`);
      return data;
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "processing" ? 3000 : false;
    },
  });

  // Extract safe properties
  const rawDoc = doc as (DocumentDetail & Record<string, any>) | undefined;
  const supplierName = rawDoc?.supplierName || rawDoc?.supplier_name || rawDoc?.originalFilename || rawDoc?.original_filename || "Invoice";
  const invoiceNumber = rawDoc?.invoiceNumber || rawDoc?.invoice_number || "";
  const invoiceDate = rawDoc?.invoiceDate || rawDoc?.invoice_date || "";
  const totalAmount = rawDoc?.totalAmount || rawDoc?.total_amount || null;
  const vatAmount = rawDoc?.vatAmount || rawDoc?.vat_amount || null;
  const currency = rawDoc?.currency || "ZAR";
  const status = rawDoc?.status || "pending";
  const extractedFields = rawDoc?.extractedFields || rawDoc?.extracted_fields || [];
  const mimeType = rawDoc?.mimeType || rawDoc?.mime_type || "application/pdf";

  // Initialise local field editing state
  useEffect(() => {
    if (extractedFields.length > 0) {
      const vals: Record<string, string> = {};
      extractedFields.forEach((f: any) => {
        const key = f.fieldName || f.field_name;
        const val = f.effectiveValue || f.effective_value || f.fieldValue || f.field_value || "";
        vals[key] = val;
      });
      setFieldValues(vals);
      setOriginalValues(vals);
    }
  }, [extractedFields.length, doc?.updatedAt]);

  // ── 2. Fetch File Blob for In-Browser Preview ───────────────────────────
  const { data: fileBlobUrl, isLoading: isLoadingFile } = useQuery({
    queryKey: ["document-file", documentId],
    queryFn: async () => {
      const res = await apiClient.get(`/v1/documents/${documentId}/file`, {
        responseType: "blob",
      });
      return URL.createObjectURL(res.data);
    },
    enabled: !!documentId && status !== "pending",
    staleTime: 5 * 60 * 1000,
  });

  // Cleanup object URL on unmount
  useEffect(() => {
    return () => {
      if (fileBlobUrl) {
        URL.revokeObjectURL(fileBlobUrl);
      }
    };
  }, [fileBlobUrl]);

  // ── 3. Mutations ────────────────────────────────────────────────────────
  // Save human field corrections
  const correctMutation = useMutation({
    mutationFn: async () => {
      const changedKeys = Object.keys(fieldValues).filter(
        (key) => fieldValues[key] !== (originalValues[key] ?? "")
      );
      if (changedKeys.length === 0) return;

      const corrections = changedKeys.map((k) => ({
        fieldName: k,
        correctedValue: fieldValues[k],
      }));

      await apiClient.patch(`/v1/documents/${documentId}/corrections`, { corrections });
    },
    onSuccess: () => {
      toast({
        title: "Corrections saved",
        description: "Extracted fields updated and versioned.",
      });
      setOriginalValues({ ...fieldValues });
      queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      queryClient.invalidateQueries({ queryKey: ["workflow-queue"] });
    },
    onError: (err: Error) => {
      toast({
        title: "Failed to save corrections",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  // Trigger processing if stuck in pending/processing
  const processMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/v1/documents/${documentId}/process?sync=true`);
    },
    onSuccess: () => {
      toast({
        title: "Processing initiated",
        description: "Extraction pipeline is running.",
      });
      refetchDoc();
    },
    onError: (err: Error) => {
      toast({
        title: "Processing failed",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  // Approve action
  const approveMutation = useMutation({
    mutationFn: async () => {
      // Save any unsaved field changes first
      const hasUnsavedChanges = Object.keys(fieldValues).some(
        (key) => fieldValues[key] !== (originalValues[key] ?? "")
      );
      if (hasUnsavedChanges) {
        await correctMutation.mutateAsync();
      }

      await apiClient.post(`/v1/workflow/${documentId}/action`, {
        action: "approve",
        comment: comment || undefined,
      });
    },
    onSuccess: () => {
      toast({ title: "Approved", description: "Invoice decision has been recorded." });
      queryClient.invalidateQueries({ queryKey: ["workflow-queue"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      navigate("/review");
    },
    onError: (err: Error) => {
      toast({
        title: "Approval failed",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  // Reject action
  const rejectMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/v1/workflow/${documentId}/action`, {
        action: "reject",
        comment: comment || undefined,
      });
    },
    onSuccess: () => {
      toast({ title: "Rejected", description: "Invoice has been marked as rejected." });
      queryClient.invalidateQueries({ queryKey: ["workflow-queue"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      navigate("/review");
    },
    onError: (err: Error) => {
      toast({
        title: "Rejection failed",
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
      navigate("/review");
    },
    onError: (err: Error) => {
      toast({ title: "Could not delete invoice", description: err.message, variant: "destructive" });
    },
  });

  if (isLoading) {
    return (
      <div className="container py-12 text-center text-muted-foreground">
        Loading document details...
      </div>
    );
  }

  if (isError || !doc) {
    return (
      <div className="container py-12 text-center space-y-4">
        <p className="text-destructive">
          Failed to load document: {(error as Error | undefined)?.message || "Document not found."}
        </p>
        <Button variant="outline" onClick={() => navigate("/review")}>
          Back to Review Queue
        </Button>
      </div>
    );
  }

  const hasDirtyFields = Object.keys(fieldValues).some(
    (key) => fieldValues[key] !== (originalValues[key] ?? "")
  );

  const isReviewerOnly = profile?.role === "reviewer";
  const isFinalApprovalStage = status === "extracted";
  const isReviewerBlockedFromFinal = isReviewerOnly && isFinalApprovalStage;

  return (
    <div className="container py-6 space-y-6 max-w-7xl">
      {/* ── Top Bar ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate("/review")}
            className="mb-1 -ml-2"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Queue
          </Button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{supplierName}</h1>
            <StatusBadge status={status as any} />
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            {invoiceNumber ? `Invoice ${invoiceNumber}` : "Pending Invoice Identification"}
            {invoiceDate && ` • Date: ${formatDate(invoiceDate)}`}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {hasDirtyFields && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => correctMutation.mutate()}
              disabled={correctMutation.isPending}
            >
              <Save className="h-4 w-4 mr-1.5" />
              {correctMutation.isPending ? "Saving..." : "Save Corrections"}
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => refetchDoc()}>
            <RotateCcw className="h-4 w-4 mr-1.5" />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive hover:text-destructive"
            disabled={deleteMutation.isPending}
            onClick={() => {
              if (window.confirm("Delete this invoice? This cannot be undone.")) {
                deleteMutation.mutate();
              }
            }}
          >
            <Trash2 className="h-4 w-4 mr-1.5" />
            {deleteMutation.isPending ? "Deleting..." : "Delete"}
          </Button>
        </div>
      </div>

      {/* ── Pending / Processing Banner ─────────────────────────────────── */}
      {(status === "pending" || status === "processing") && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-4 w-4 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
            <div>
              <p className="font-medium text-blue-900">
                Document is currently being processed by AI
              </p>
              <p className="text-xs text-blue-700">
                OCR and automated field extraction are in progress. This page will refresh
                automatically.
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => processMutation.mutate()}
            disabled={processMutation.isPending}
          >
            <Play className="h-3.5 w-3.5 mr-1.5" />
            {processMutation.isPending ? "Processing..." : "Process Now (Dev Trigger)"}
          </Button>
        </div>
      )}

      {/* ── Key Metrics Summary Cards ────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-xs text-muted-foreground">Total Amount</p>
            <p className="text-xl font-bold">{formatCurrency(totalAmount, currency)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-xs text-muted-foreground">VAT / Tax</p>
            <p className="text-lg font-semibold">{formatCurrency(vatAmount, currency)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-xs text-muted-foreground">Invoice Date</p>
            <p className="text-lg font-semibold">{formatDate(invoiceDate)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-xs text-muted-foreground">Currency</p>
            <p className="text-lg font-semibold">{currency}</p>
          </CardContent>
        </Card>
      </div>

      {/* ── Main Split View: Original Document vs Extracted Fields ───────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Document File Preview (5 cols) */}
        <div className="lg:col-span-6 space-y-4">
          <Card className="overflow-hidden">
            <CardHeader className="py-3 px-4 border-b bg-muted/30">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  Original Document Preview
                </CardTitle>
                {fileBlobUrl && (
                  <a
                    href={fileBlobUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-primary hover:underline"
                  >
                    Open in new tab
                  </a>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0 bg-muted/20 min-h-[500px] flex items-center justify-center">
              {isLoadingFile ? (
                <div className="text-center p-8 text-sm text-muted-foreground">
                  Loading preview...
                </div>
              ) : fileBlobUrl ? (
                mimeType.includes("pdf") ? (
                  <iframe
                    src={fileBlobUrl}
                    title="Invoice PDF Preview"
                    className="w-full h-[650px] border-0"
                  />
                ) : (
                  <div className="p-4 flex items-center justify-center max-h-[650px] overflow-auto">
                    <img
                      src={fileBlobUrl}
                      alt="Invoice Preview"
                      className="max-w-full h-auto object-contain rounded shadow-sm"
                    />
                  </div>
                )
              ) : (
                <div className="text-center p-8 text-sm text-muted-foreground">
                  <FileText className="h-10 w-10 mx-auto mb-2 opacity-40" />
                  Preview not available for this document status.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Editable Fields & Actions (7 cols) */}
        <div className="lg:col-span-6 space-y-6">
          {/* Extracted Fields Form */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">Extracted Fields</CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    Review values against the document. Click any field to edit before approving.
                  </CardDescription>
                </div>
                {hasDirtyFields && (
                  <span className="text-xs font-medium px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                    Unsaved changes
                  </span>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {extractedFields.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground text-sm">
                  {status === "pending" || status === "processing"
                    ? "Fields will appear here once extraction is complete."
                    : "No fields were extracted from this document."}
                </div>
              ) : (
                <div className="space-y-3 divide-y">
                  {extractedFields.map((f: any) => {
                    const key = f.fieldName || f.field_name;
                    const confidence = f.confidenceScore ?? f.confidence_score ?? 0;
                    const validationMessage = f.validationMessage || f.validation_message;
                    const validationStatus = f.validationStatus || f.validation_status;
                    const isWarning = validationStatus === "warning" || confidence < 0.8;
                    const isFieldDirty = fieldValues[key] !== (originalValues[key] ?? "");

                    return (
                      <div key={f.id || key} className="pt-3 first:pt-0 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            {key.replace(/_/g, " ")}
                          </label>
                          <div className="flex items-center gap-2">
                            {isFieldDirty && (
                              <span className="text-[10px] text-primary font-medium">Modified</span>
                            )}
                            <ConfidenceBar score={confidence} showLabel />
                          </div>
                        </div>

                        <Input
                          value={fieldValues[key] ?? ""}
                          onChange={(e) =>
                            setFieldValues((prev) => ({
                              ...prev,
                              [key]: e.target.value,
                            }))
                          }
                          className={`text-sm ${
                            isWarning ? "border-yellow-400 bg-yellow-50/20" : ""
                          }`}
                          placeholder={`Enter ${key.replace(/_/g, " ")}`}
                        />

                        {validationMessage && (
                          <div className="flex items-center gap-1.5 text-xs text-yellow-700 mt-1">
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                            <span>{validationMessage}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {hasDirtyFields && (
                <Button
                  onClick={() => correctMutation.mutate()}
                  disabled={correctMutation.isPending}
                  className="w-full mt-4"
                  variant="secondary"
                >
                  <Save className="h-4 w-4 mr-2" />
                  {correctMutation.isPending ? "Saving changes..." : "Save Field Corrections"}
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Decision Box */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Decision & Workflow</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isReviewerBlockedFromFinal && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800 flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>
                    <strong>Approver Sign-off Required:</strong> This invoice has passed reviewer
                    check and is awaiting sign-off by an Approver or Admin.
                  </span>
                </div>
              )}

              <textarea
                placeholder="Add an optional comment or note for the audit trail..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                rows={2}
              />

              <div className="flex gap-3">
                <Button
                  variant="destructive"
                  onClick={() => rejectMutation.mutate()}
                  disabled={rejectMutation.isPending || status === "pending" || status === "rejected"}
                  className="flex-1"
                >
                  <X className="h-4 w-4 mr-1.5" />
                  {rejectMutation.isPending ? "Rejecting..." : "Reject"}
                </Button>

                <Button
                  onClick={() => approveMutation.mutate()}
                  disabled={
                    approveMutation.isPending ||
                    status === "pending" ||
                    status === "approved" ||
                    isReviewerBlockedFromFinal
                  }
                  className="flex-1"
                >
                  <Check className="h-4 w-4 mr-1.5" />
                  {approveMutation.isPending
                    ? "Approving..."
                    : isFinalApprovalStage
                    ? "Final Approval"
                    : "Approve Review"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
