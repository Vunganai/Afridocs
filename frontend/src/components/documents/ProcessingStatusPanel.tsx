import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/useToast";
import { Check, Circle, Loader2, Play, XCircle } from "lucide-react";

export interface ProcessingStep {
  id: string;
  label: string;
  state: "pending" | "active" | "done" | "error" | string;
}

export interface ProcessingProgress {
  documentId?: string;
  document_id?: string;
  filename: string;
  status: string;
  stage: string;
  percent: number;
  message: string;
  done: boolean;
  error?: string | null;
  steps: ProcessingStep[];
}

export function ProcessingStatusPanel({ documentId }: { documentId: string }) {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isError, error, isLoading } = useQuery({
    queryKey: ["document-progress", documentId],
    queryFn: async () => {
      const { data } = await apiClient.get<ProcessingProgress>(
        `/v1/documents/${documentId}/progress`
      );
      return data;
    },
    enabled: !!documentId,
    refetchInterval: (query) => (query.state.data?.done ? false : 800),
    staleTime: 0,
  });

  const processMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/v1/documents/${documentId}/process?sync=true`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document-progress", documentId] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-metrics"] });
    },
    onError: (err: Error) => {
      toast({ title: "Could not start processing", description: err.message, variant: "destructive" });
    },
  });

  const percent = data?.percent ?? 0;
  const status = data?.status ?? "pending";
  const done = data?.done ?? false;
  const failed = status === "failed";
  const reviewStatus = status === "review_required" || status === "extracted";

  return (
    <Card>
      <CardHeader className="text-center space-y-2">
        <div className="mx-auto mb-2">
          {failed ? (
            <XCircle className="h-10 w-10 text-destructive" />
          ) : done ? (
            <Check className="h-10 w-10 text-green-600" />
          ) : (
            <Loader2 className="h-10 w-10 text-primary animate-spin" />
          )}
        </div>
        <CardTitle>
          {failed ? "Processing failed" : done ? "Processing complete" : "Processing invoice"}
        </CardTitle>
        <CardDescription className="break-all">
          {data?.filename || (isLoading ? "Starting processing..." : "Uploaded document")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <div className="flex justify-between text-sm mb-2 gap-4">
            <span className="text-muted-foreground">{data?.message || "Starting..."}</span>
            <span className="font-medium tabular-nums shrink-0">{percent}%</span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                failed ? "bg-destructive" : "bg-primary"
              }`}
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>

        <ol className="space-y-3">
          {(data?.steps || []).map((step) => (
            <li key={step.id} className="flex items-center gap-3 text-sm">
              {step.state === "done" ? (
                <Check className="h-4 w-4 text-green-600 shrink-0" />
              ) : step.state === "error" ? (
                <XCircle className="h-4 w-4 text-destructive shrink-0" />
              ) : step.state === "active" ? (
                <Loader2 className="h-4 w-4 text-primary animate-spin shrink-0" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground/40 shrink-0" />
              )}
              <span
                className={
                  step.state === "pending"
                    ? "text-muted-foreground"
                    : step.state === "active"
                    ? "font-medium text-foreground"
                    : ""
                }
              >
                {step.label}
              </span>
            </li>
          ))}
        </ol>

        {isError && (
          <p className="text-sm text-destructive text-center">{(error as Error).message}</p>
        )}

        {data?.error && failed && (
          <p className="text-sm text-destructive bg-destructive/10 rounded p-3">{data.error}</p>
        )}

        {!done && status === "pending" && (
          <Button
            variant="outline"
            className="w-full"
            disabled={processMutation.isPending}
            onClick={() => processMutation.mutate()}
          >
            <Play className="h-4 w-4 mr-2" />
            {processMutation.isPending ? "Starting..." : "Process now"}
          </Button>
        )}

        {done && (
          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" onClick={() => navigate("/documents")}>
              All invoices
            </Button>
            <Button
              className="flex-1"
              onClick={() =>
                navigate(reviewStatus ? `/review/${documentId}` : `/documents/${documentId}`)
              }
            >
              {reviewStatus ? "Review invoice" : "View invoice"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
