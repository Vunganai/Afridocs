"""
Pydantic schemas for Document API requests and responses.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import CamelModel

# ── Extracted Field ────────────────────────────────────────────────────────

class ExtractedFieldSchema(CamelModel):
    id: UUID
    field_name: str
    field_value: str | None
    confidence_score: float | None
    was_corrected: bool
    corrected_value: str | None
    validation_status: str
    validation_message: str | None
    effective_value: str | None = None


class ExtractedFieldCorrection(CamelModel):
    field_name: str
    corrected_value: str


# ── Document ───────────────────────────────────────────────────────────────

class DocumentListItem(CamelModel):
    """Lightweight document representation for list views."""
    id: UUID
    original_filename: str
    document_type: str
    status: str
    ingestion_channel: str
    invoice_number: str | None
    invoice_date: date | None
    supplier_name: str | None
    total_amount: Decimal | None
    currency: str
    is_duplicate: bool
    has_validation_warnings: bool
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentListItem):
    """Full document detail including extracted fields."""
    file_size_bytes: int
    mime_type: str
    classification_confidence: float | None
    due_date: date | None
    supplier_vat_number: str | None
    vat_amount: Decimal | None
    extracted_data: dict | None
    processing_error: str | None
    extracted_fields: list[ExtractedFieldSchema] = []
    uploaded_by_id: UUID | None
    duplicate_of_id: UUID | None


class DocumentStatusUpdate(CamelModel):
    """Used internally — not exposed directly to API callers."""
    status: str
    processing_error: str | None = None


# ── Upload ─────────────────────────────────────────────────────────────────

class ProcessingStep(CamelModel):
    id: str
    label: str
    state: str


class ProcessingProgress(CamelModel):
    document_id: UUID
    filename: str
    status: str
    stage: str
    percent: int
    message: str
    done: bool
    error: str | None = None
    steps: list[ProcessingStep]


class UploadResponse(CamelModel):
    document_id: UUID
    status: str
    message: str


# ── Corrections ───────────────────────────────────────────────────────────

class DocumentCorrectionsRequest(CamelModel):
    corrections: list[ExtractedFieldCorrection] = Field(min_length=1)


# ── Review / Approval ──────────────────────────────────────────────────────

class WorkflowActionRequest(CamelModel):
    action: str = Field(pattern="^(approve|reject)$")
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def strip_comment(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class WorkflowStepSchema(CamelModel):
    id: UUID
    step_number: int
    step_type: str
    status: str
    assigned_to_id: UUID | None
    action_taken_by_id: UUID | None
    actioned_at: datetime | None
    comment: str | None
    created_at: datetime


# ── Search / Filter ────────────────────────────────────────────────────────

class DocumentSearchParams(CamelModel):
    """Query parameters for document list/search endpoints."""
    status: str | None = None
    supplier_name: str | None = None
    invoice_number: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ── Export ─────────────────────────────────────────────────────────────────

class ExportRequest(CamelModel):
    format: str = Field(default="csv", pattern="^(csv|json)$")
    document_ids: list[UUID] | None = None  # None = export all matching current filter
