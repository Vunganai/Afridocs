import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import { useToast } from "@/hooks/useToast";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { DocumentDetail } from "@/types";
import { Check, X } from "lucide-react";

export function ReviewDetailPage() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [comment, setComment] = useState("");

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", documentId],
    queryFn: async () => {
      const { data } = await apiClient.get<DocumentDetail>(`/v1/documents/${documentId}`);
      return data;
    },
  });

  const approveMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/v1/workflow/${documentId}/action`, {
        action: "approve",
        comment: comment || undefined,
      });
    },
    onSuccess: () => {
      toast({ title: "Approved", description: "Invoice has been approved." });
      navigate("/review");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/v1/workflow/${documentId}/action`, {
        action: "reject",
        comment: comment || undefined,
      });
    },
    onSuccess: () => {
      toast({ title: "Rejected", description: "Invoice has been rejected." });
      navigate("/review");
    },
  });

  if (isLoading || !doc) return <div className="container py-8">Loading...</div>;

  return (
    <div className="container py-8 space-y-6 max-w-4xl">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">{doc.supplierName}</h1>
          <p className="text-muted-foreground">Invoice {doc.invoiceNumber || "—"}</p>
        </div>
        <Button variant="outline" onClick={() => navigate("/review")}>
          Back to queue
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Amount</p>
            <p className="text-2xl font-bold">{formatCurrency(doc.totalAmount, doc.currency)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Invoice Date</p>
            <p className="text-lg font-semibold">{formatDate(doc.invoiceDate)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">VAT</p>
            <p className="text-lg font-semibold">{formatCurrency(doc.vatAmount, doc.currency)}</p>
          </CardContent>
        </Card>
      </div>

      {doc.extractedFields.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Extracted Fields</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {doc.extractedFields.map((f) => (
              <div key={f.id} className="flex items-start justify-between p-3 bg-muted/50 rounded">
                <div className="flex-1">
                  <p className="font-medium text-sm">{f.fieldName}</p>
                  <p className="text-sm text-foreground">{f.effectiveValue || "—"}</p>
                  {f.validationMessage && (
                    <p className="text-xs text-muted-foreground mt-1">{f.validationMessage}</p>
                  )}
                </div>
                <ConfidenceBar score={f.confidenceScore} showLabel />
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Decision</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea
            placeholder="Add a comment (optional)..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="w-full px-3 py-2 border rounded-md text-sm"
            rows={3}
          />
          <div className="flex gap-2">
            <Button
              variant="destructive"
              onClick={() => rejectMutation.mutate()}
              disabled={rejectMutation.isPending}
              className="flex-1"
            >
              <X className="h-4 w-4 mr-2" />
              Reject
            </Button>
            <Button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending}
              className="flex-1"
            >
              <Check className="h-4 w-4 mr-2" />
              Approve
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
