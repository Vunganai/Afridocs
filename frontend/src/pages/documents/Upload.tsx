import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ProcessingStatusPanel } from "@/components/documents/ProcessingStatusPanel";
import { useToast } from "@/hooks/useToast";
import { Upload } from "lucide-react";

function extractDocumentId(payload: Record<string, unknown> | undefined): string | null {
  if (!payload) return null;
  const raw = payload.documentId ?? payload.document_id ?? payload.id;
  if (raw == null) return null;
  const id = String(raw).trim();
  return id && id !== "undefined" && id !== "null" ? id : null;
}

export function UploadPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const onDrop = async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length) return;
    setUploading(true);
    try {
      const file = acceptedFiles[0];
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await apiClient.post("/v1/documents", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const docId = extractDocumentId(data as Record<string, unknown>);
      queryClient.invalidateQueries({ queryKey: ["dashboard-metrics"] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (!docId) {
        toast({
          title: "Uploaded, but could not open processing view",
          description: "Open Invoices and select the document to continue.",
        });
        return;
      }
      setProcessingId(docId);
      navigate(`/documents/${docId}/processing`, { replace: true });
    } catch (err) {
      toast({
        title: "Upload failed",
        description: (err as Error).message,
      });
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "image/*": [".jpg", ".png", ".tiff"] },
    maxFiles: 1,
    disabled: uploading,
  });

  if (processingId) {
    return (
      <div className="container max-w-xl py-12">
        <ProcessingStatusPanel documentId={processingId} />
      </div>
    );
  }

  return (
    <div className="container max-w-2xl py-8">
      <Card>
        <CardHeader>
          <CardTitle>Upload invoices</CardTitle>
          <CardDescription>Drag & drop or click to select a PDF or image file</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition ${
              isDragActive ? "border-primary bg-primary/5" : "border-muted"
            } ${uploading ? "pointer-events-none opacity-80" : "cursor-pointer"}`}
          >
            <input {...getInputProps()} />
            <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            {uploading ? (
              <p className="font-medium text-primary animate-pulse">Uploading invoice...</p>
            ) : isDragActive ? (
              <p>Drop the file here...</p>
            ) : (
              <div>
                <p className="font-medium">Drag a file here, or click to select</p>
                <p className="text-sm text-muted-foreground">PDF, JPG, PNG, TIFF • Max 20 MB</p>
              </div>
            )}
          </div>

          <Button onClick={() => navigate("/documents")} variant="outline" className="w-full">
            All Invoices
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
