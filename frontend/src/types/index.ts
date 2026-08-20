// ── Auth / User ────────────────────────────────────────────────────────────

export interface UserProfile {
  id: string;
  supabaseUserId: string;
  tenantId: string;
  email: string;
  fullName: string | null;
  avatarUrl: string | null;
  role: "admin" | "reviewer" | "approver" | "viewer";
  isActive: boolean;
  createdAt: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  contactEmail: string;
  countryCode: string;
  plan: string;
  monthlyDocumentLimit: number;
  defaultCurrency: string;
  approvalThresholdAmount: string | null;
  isActive: boolean;
  createdAt: string;
}

// ── Documents ──────────────────────────────────────────────────────────────

export type DocumentStatus =
  | "pending"
  | "processing"
  | "extracted"
  | "review_required"
  | "approved"
  | "rejected"
  | "duplicate"
  | "failed";

export interface DocumentListItem {
  id: string;
  originalFilename: string;
  documentType: string;
  status: DocumentStatus;
  ingestionChannel: string;
  invoiceNumber: string | null;
  invoiceDate: string | null;
  supplierName: string | null;
  totalAmount: string | null;
  currency: string;
  isDuplicate: boolean;
  hasValidationWarnings: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ExtractedField {
  id: string;
  fieldName: string;
  fieldValue: string | null;
  confidenceScore: number | null;
  wasCorrected: boolean;
  correctedValue: string | null;
  validationStatus: "pending" | "valid" | "invalid" | "warning" | "skipped";
  validationMessage: string | null;
  effectiveValue: string | null;
}

export interface DocumentDetail extends DocumentListItem {
  fileSizeBytes: number;
  mimeType: string;
  classificationConfidence: number | null;
  dueDate: string | null;
  supplierVatNumber: string | null;
  vatAmount: string | null;
  extractedData: Record<string, unknown> | null;
  processingError: string | null;
  extractedFields: ExtractedField[];
  uploadedById: string | null;
  duplicateOfId: string | null;
}

// ── Workflow ───────────────────────────────────────────────────────────────

export interface WorkflowStep {
  id: string;
  stepNumber: number;
  stepType: string;
  status: "pending" | "approved" | "rejected" | "skipped";
  assignedToId: string | null;
  actionTakenById: string | null;
  actionedAt: string | null;
  comment: string | null;
  createdAt: string;
}

// ── Dashboard ──────────────────────────────────────────────────────────────

export interface DashboardMetrics {
  totalDocuments: number;
  processedLast7Days: number;
  processedLast30Days: number;
  pendingReview: number;
  approved: number;
  rejected: number;
  duplicatesCaught: number;
  statusBreakdown: Array<{ status: string; count: number }>;
}

// ── API responses ──────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}

export interface UploadResponse {
  documentId: string;
  status: string;
  message: string;
}

export interface MessageResponse {
  message: string;
}
