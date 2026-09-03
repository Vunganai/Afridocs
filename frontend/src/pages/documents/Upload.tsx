import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/useToast";
import { Upload, FileCheck } from "lucide-react";

export function UploadPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; id: string }>>([]);

  const onDrop = async (acceptedFiles: File[]) => {
    setUploading(true);
    for (const file of acceptedFiles) {
      try {
        const formData = new FormData();
        formData.append("file", file);
        const { data } = await apiClient.post("/v1/documents", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        const docId = data.documentId || data.document_id;
        setUploadedFiles((prev) => [...prev, { name: file.name, id: docId }]);
        // Invalidate dashboard and document list so metrics reflect the new upload immediately
        queryClient.invalidateQueries({ queryKey: ["dashboard-metrics"] });
        queryClient.invalidateQueries({ queryKey: ["documents"] });
        toast({ title: "Uploaded", description: `${file.name} uploaded successfully.` });
      } catch (err) {
        toast({
          title: "Upload failed",
          description: (err as Error).message,
        });
      }
    }
    setUploading(false);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "image/*": [".jpg", ".png", ".tiff"] },
  });

  return (
    <div className="container max-w-2xl py-8">
      <Card>
        <CardHeader>
          <CardTitle>Upload invoices</CardTitle>
          <CardDescription>Drag & drop or click to select PDF or image files</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center transition ${
              isDragActive ? "border-primary bg-primary/5" : "border-muted"
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            {uploading ? (
              <p className="font-medium text-primary animate-pulse">Uploading and preparing document(s)...</p>
            ) : isDragActive ? (
              <p>Drop the files here...</p>
            ) : (
              <div>
                <p className="font-medium">Drag files here, or click to select</p>
                <p className="text-sm text-muted-foreground">PDF, JPG, PNG, TIFF • Max 20 MB</p>
              </div>
            )}
          </div>

          {uploadedFiles.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Uploaded ({uploadedFiles.length})</h3>
              {uploadedFiles.map((f) => (
                <div key={f.id} className="flex items-center justify-between p-2.5 bg-muted rounded">
                  <div className="flex items-center gap-2 truncate">
                    <FileCheck className="h-4 w-4 text-green-600 shrink-0" />
                    <span className="text-sm truncate">{f.name}</span>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => navigate(`/documents/${f.id}`)}
                  >
                    View &rarr;
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <Button onClick={() => navigate("/documents")} variant="outline" className="flex-1">
              All Invoices
            </Button>
            <Button
              onClick={() => navigate("/review")}
              disabled={uploadedFiles.length === 0}
              className="flex-1"
            >
              Go to Review Queue &rarr;
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
