import { useParams } from "react-router-dom";
import { ProcessingStatusPanel } from "@/components/documents/ProcessingStatusPanel";

export function ProcessingPage() {
  const { documentId } = useParams<{ documentId: string }>();

  if (!documentId) {
    return (
      <div className="container max-w-xl py-12 text-center text-muted-foreground">
        Missing document id.
      </div>
    );
  }

  return (
    <div className="container max-w-xl py-12">
      <ProcessingStatusPanel documentId={documentId} />
    </div>
  );
}
