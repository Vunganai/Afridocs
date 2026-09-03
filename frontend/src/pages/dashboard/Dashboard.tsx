import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { DashboardMetrics } from "@/types";
import { Upload, CheckCircle2, AlertCircle } from "lucide-react";

export function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Always bust the cache when the Dashboard mounts so we never show stale zeros
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ["dashboard-metrics"] });
  }, [queryClient]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard-metrics"],
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardMetrics>("/v1/dashboard/metrics");
      return data;
    },
    staleTime: 0,
    refetchInterval: 15_000,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  });

  const rawData = data as (DashboardMetrics & Record<string, any>) | undefined;
  const totalDocs = rawData?.totalDocuments ?? rawData?.total_documents ?? 0;
  const processed7d = rawData?.processedLast7Days ?? rawData?.processed_last_7_days ?? 0;
  const processed30d = rawData?.processedLast30Days ?? rawData?.processed_last_30_days ?? 0;
  const pendingReview = rawData?.pendingReview ?? rawData?.pending_review ?? 0;
  const approvedCount = rawData?.approved ?? 0;
  const statusBreakdown = rawData?.statusBreakdown || rawData?.status_breakdown || [];

  const metrics = [
    { label: "Total Invoices", value: totalDocs },
    { label: "Processed (7d)", value: processed7d },
    { label: "Processed (30d)", value: processed30d },
    { label: "Pending Review", value: pendingReview },
  ];

  return (
    <div className="container py-8 space-y-8 max-w-6xl">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Invoice processing overview</p>
        </div>
        <Button onClick={() => navigate("/upload")}>
          <Upload className="h-4 w-4 mr-2" />
          Upload invoices
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading metrics...</div>
      ) : error ? (
        <div className="text-center py-12 text-destructive">
          Failed to load metrics: {(error as Error).message}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {metrics.map((m) => (
              <Card key={m.label}>
                <CardContent className="pt-6">
                  <div className="text-3xl font-bold">{m.value}</div>
                  <p className="text-sm text-muted-foreground mt-1">{m.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          <Separator />

          {/* Status Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Invoice Status</CardTitle>
            </CardHeader>
            <CardContent>
              {statusBreakdown.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No invoice status data available yet.
                </p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {statusBreakdown.map((s: any) => (
                    <div key={s.status} className="text-center">
                      <div className="text-2xl font-bold text-primary">{s.count}</div>
                      <p className="text-sm text-muted-foreground capitalize">
                        {s.status.replace(/_/g, " ")}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Card
              className="hover:bg-accent/50 cursor-pointer transition border"
              onClick={() => navigate("/review")}
            >
              <CardContent className="p-6 text-center">
                <AlertCircle className="h-8 w-8 mx-auto mb-2 text-yellow-500" />
                <p className="font-medium text-lg">{pendingReview} Invoices</p>
                <p className="text-xs text-muted-foreground">Awaiting Review &rarr;</p>
              </CardContent>
            </Card>
            <Card
              className="hover:bg-accent/50 cursor-pointer transition border"
              onClick={() => navigate("/documents")}
            >
              <CardContent className="p-6 text-center">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-600" />
                <p className="font-medium text-lg">{approvedCount} Approved</p>
                <p className="text-xs text-muted-foreground">View all invoices &rarr;</p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
