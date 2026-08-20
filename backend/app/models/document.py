"""
Document and related models.

Document          — the uploaded file record
ExtractedField    — one row per extracted field from a document
DocumentVersion   — audit trail of re-processed versions
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.workflow import WorkflowStep


# ── Document Status enum values ────────────────────────────────────────────
class DocumentStatus:
    PENDING = "pending"           # Uploaded, not yet processed
    PROCESSING = "processing"     # Celery task running
    EXTRACTED = "extracted"       # AI extraction complete, no flags
    REVIEW_REQUIRED = "review_required"  # Low confidence or validation flags
    APPROVED = "approved"         # Approved by authorised user
    REJECTED = "rejected"         # Rejected
    DUPLICATE = "duplicate"       # Duplicate detected
    FAILED = "failed"             # Processing error


class Document(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A document uploaded by a user within a tenant.
    MVP: invoices only.
    """

    __tablename__ = "documents"

    # Ownership
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Azure Blob Storage path or local path in dev",
    )
    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 of the file content for duplicate detection",
    )

    # Document type
    document_type: Mapped[str] = mapped_column(
        String(50),
        default="invoice",
        nullable=False,
        index=True,
    )

    # Processing status
    status: Mapped[str] = mapped_column(
        String(50),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI classification confidence
    classification_confidence: Mapped[float | None] = mapped_column(nullable=True)

    # Ingestion channel
    ingestion_channel: Mapped[str] = mapped_column(
        String(50),
        default="upload",
        nullable=False,
        comment="upload | email | api",
    )

    # Extracted invoice data (denormalised for query speed)
    invoice_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    supplier_vat_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    vat_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="ZAR", nullable=False)

    # Raw AI output (full extracted JSON, all fields + confidence scores)
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Flags
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    has_validation_warnings: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="documents")
    uploaded_by: Mapped["User | None"] = relationship("User", foreign_keys=[uploaded_by_id])
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        "ExtractedField", back_populates="document", cascade="all, delete-orphan"
    )
    workflow_steps: Mapped[list["WorkflowStep"]] = relationship(
        "WorkflowStep", back_populates="document", cascade="all, delete-orphan"
    )
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} type={self.document_type!r} "
            f"status={self.status!r} invoice={self.invoice_number!r}>"
        )


class ExtractedField(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Individual field extracted from a document by the AI pipeline.
    Keeps confidence scores and tracks human corrections.
    """

    __tablename__ = "extracted_fields"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)

    # Human correction tracking
    was_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Validation
    validation_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        comment="pending | valid | invalid | warning",
    )
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="extracted_fields")

    @property
    def effective_value(self) -> str | None:
        """Return the human-corrected value if available, otherwise AI value."""
        return self.corrected_value if self.was_corrected else self.field_value

    def __repr__(self) -> str:
        return (
            f"<ExtractedField {self.field_name}={self.effective_value!r} "
            f"confidence={self.confidence_score}>"
        )


class DocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Version history for a document's extracted data.
    Created whenever a re-extraction or human correction is saved.
    """

    __tablename__ = "document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full snapshot of extracted_data at this version",
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
