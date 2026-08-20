import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { DocumentListItem, PaginatedResponse } from "@/types";
import { Upload, Eye } from "lucide-react";

export function DocumentListPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: async () => {
      const { data } = await apiClient.get<PaginatedResponse<DocumentListItem>>("/v1/documents");
      return data;
    },
  });

  return (
    <div className="container py-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Invoices</h1>
          <p className="text-muted-foreground">View and manage all processed invoices</p>
        </div>
        <Button onClick={() => navigate("/upload")}>
          <Upload className="h-4 w-4 mr-2" />
          Upload
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading...</div>
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
          {data.items.map((doc) => (
            <Card key={doc.id} className="hover:bg-accent/50 cursor-pointer transition" onClick={() => navigate(`/documents/${doc.id}`)}>
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{doc.supplierName || doc.originalFilename}</p>
                  <p className="text-sm text-muted-foreground">
                    {doc.invoiceNumber ? `Invoice ${doc.invoiceNumber}` : doc.originalFilename}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  {doc.invoiceDate && <span className="text-sm text-muted-foreground">{formatDate(doc.invoiceDate)}</span>}
                  {doc.totalAmount && <span className="font-mono text-sm">{formatCurrency(doc.totalAmount, doc.currency)}</span>}
                  <StatusBadge status={doc.status} />
                  <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); navigate(`/documents/${doc.id}`); }}>
                    <Eye className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
