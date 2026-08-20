import { useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/useToast";
import { Upload, FileCheck } from "lucide-react";

export function UploadPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
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
        setUploadedFiles((prev) => [...prev, { name: file.name, id: data.document_id }]);
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
            {isDragActive ? (
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
                <div key={f.id} className="flex items-center gap-2 p-2 bg-muted rounded">
                  <FileCheck className="h-4 w-4 text-green-600" />
                  <span className="text-sm flex-1 truncate">{f.name}</span>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <Button onClick={() => navigate("/")} variant="outline" className="flex-1">
              Back
            </Button>
            <Button onClick={() => navigate("/")} disabled={uploadedFiles.length === 0} className="flex-1">
              Continue
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
