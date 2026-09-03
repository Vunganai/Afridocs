import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { DashboardMetrics } from "@/types";
import { Upload, CheckCircle2, AlertCircle, Copy } from "lucide-react";

export function DashboardPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-metrics"],
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardMetrics>("/v1/dashboard/metrics");
      return data;
    },
    refetchInterval: 30_000,
  });

  const metrics = [
    { label: "Total Invoices", value: data?.total_documents || 0 },
    { label: "Processed (7d)", value: data?.processed_last_7_days || 0 },
    { label: "Processed (30d)", value: data?.processed_last_30_days || 0 },
    { label: "Pending Review", value: data?.pending_review || 0 },
  ];

  return (
    <div className="container py-8 space-y-8">
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
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {data?.status_breakdown?.map((s) => (
                  <div key={s.status} className="text-center">
                    <div className="text-2xl font-bold text-afri-green">{s.count}</div>
                    <p className="text-sm text-muted-foreground capitalize">{s.status.replace("_", " ")}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <div className="grid grid-cols-2 gap-4">
            <Card className="hover:bg-accent/50 cursor-pointer transition">
              <CardContent className="p-6 text-center" onClick={() => navigate("/review")}>
                <AlertCircle className="h-8 w-8 mx-auto mb-2 text-yellow-500" />
                <p className="font-medium">{data?.pending_review || 0} Pending</p>
                <p className="text-xs text-muted-foreground">awaiting review</p>
              </CardContent>
            </Card>
            <Card className="hover:bg-accent/50 cursor-pointer transition">
              <CardContent className="p-6 text-center" onClick={() => navigate("/documents")}>
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-600" />
                <p className="font-medium">{data?.approved || 0} Approved</p>
                <p className="text-xs text-muted-foreground">ready to export</p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
