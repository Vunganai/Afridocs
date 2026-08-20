import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/utils";
import type { DocumentDetail } from "@/types";
import { ArrowLeft, AlertTriangle, Copy } from "lucide-react";

export function DocumentDetailPage() {
  const { documentId } = useParams();
  const navigate = useNavigate();

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", documentId],
    queryFn: async () => {
      const { data } = await apiClient.get<DocumentDetail>(`/v1/documents/${documentId}`);
      return data;
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

  return (
    <div className="container py-8 max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Button variant="ghost" size="sm" onClick={() => navigate("/documents")} className="mb-2 -ml-2">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <h1 className="text-2xl font-bold">{doc.supplierName || doc.originalFilename}</h1>
          <div className="flex items-center gap-2 mt-1">
            {doc.invoiceNumber && (
              <span className="text-sm text-muted-foreground">Invoice {doc.invoiceNumber}</span>
            )}
            <StatusBadge status={doc.status} />
            {doc.isDuplicate && (
              <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded flex items-center gap-1">
                <Copy className="h-3 w-3" /> Duplicate
              </span>
            )}
          </div>
        </div>

        {/* Action button for review-eligible docs */}
        {(doc.status === "review_required" || doc.status === "extracted") && (
          <Button onClick={() => navigate(`/review/${doc.id}`)}>Review &amp; Approve</Button>
        )}
      </div>

      {/* Key figures */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Total Amount</p>
            <p className="text-xl font-bold">{formatCurrency(doc.totalAmount, doc.currency)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">VAT</p>
            <p className="text-xl font-bold">{formatCurrency(doc.vatAmount, doc.currency)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Invoice Date</p>
            <p className="text-xl font-bold">{formatDate(doc.invoiceDate)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-xs text-muted-foreground">Due Date</p>
            <p className="text-xl font-bold">{formatDate(doc.dueDate)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Warnings */}
      {doc.hasValidationWarnings && (
        <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>This document has validation warnings. Review the extracted fields below.</span>
        </div>
      )}

      {/* Processing error */}
      {doc.processingError && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded text-sm text-destructive">
          Processing error: {doc.processingError}
        </div>
      )}

      {/* Extracted Fields */}
      {doc.extractedFields.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Extracted Fields</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {doc.extractedFields.map((f) => (
                <div key={f.id} className="flex items-center justify-between py-3 gap-4">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium capitalize">
                      {f.fieldName.replace(/_/g, " ")}
                    </p>
                    <p className="text-sm text-foreground truncate">
                      {f.effectiveValue || "—"}
                      {f.wasCorrected && (
                        <span className="ml-2 text-xs text-green-600">(corrected)</span>
                      )}
                    </p>
                    {f.validationMessage && f.validationStatus !== "valid" && (
                      <p className="text-xs text-muted-foreground mt-0.5">{f.validationMessage}</p>
                    )}
                  </div>
                  <div className="shrink-0">
                    <ConfidenceBar score={f.confidenceScore} showLabel />
                  </div>
                </div>
              ))}
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
            <p className="font-medium truncate">{doc.originalFilename}</p>
          </div>
          <div>
            <p className="text-muted-foreground">MIME type</p>
            <p className="font-medium">{doc.mimeType}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Size</p>
            <p className="font-medium">{(doc.fileSizeBytes / 1024).toFixed(1)} KB</p>
          </div>
          <div>
            <p className="text-muted-foreground">Uploaded</p>
            <p className="font-medium">{formatDateTime(doc.createdAt)}</p>
          </div>
          {doc.classificationConfidence !== null && (
            <div>
              <p className="text-muted-foreground">Classification confidence</p>
              <ConfidenceBar score={doc.classificationConfidence} showLabel />
            </div>
          )}
          <div>
            <p className="text-muted-foreground">Channel</p>
            <p className="font-medium capitalize">{doc.ingestionChannel}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
