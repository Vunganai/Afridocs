"""
Workflow models — approval steps and audit events.

WorkflowStep  — one row per approval action on a document
AuditEvent    — immutable append-only log of all significant actions
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.user import User


class WorkflowStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single step in the approval workflow for a document.
    MVP supports 2 levels: reviewer (level 1) and approver (level 2).
    """

    __tablename__ = "workflow_steps"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Step definition
    step_number: Mapped[int] = mapped_column(nullable=False, comment="1=review, 2=approve")
    step_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="review | approve | reject | escalate",
    )

    # Assignment
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Outcome
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        comment="pending | approved | rejected | skipped",
    )
    action_taken_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="workflow_steps")
    assigned_to: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_to_id]
    )
    actioned_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[action_taken_by_id]
    )

    def __repr__(self) -> str:
        return (
            f"<WorkflowStep doc={self.document_id} "
            f"step={self.step_number} status={self.status!r}>"
        )


class AuditEvent(UUIDPrimaryKeyMixin, Base):
    """
    Immutable audit log. Never updated or deleted.
    Records every significant action in the system for compliance (POPIA/SOC2).
    """

    __tablename__ = "audit_events"

    # Immutable timestamp — NOT using server_default to guarantee accuracy
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Context
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User who performed the action (NULL for system actions)",
    )
    actor_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Denormalised — preserved even if user is deleted",
    )

    # Event
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="e.g. document.uploaded, document.approved, user.login",
    )
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Payload — named event_metadata to avoid collision with SQLAlchemy's reserved 'metadata'
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # keep the DB column name as 'metadata' for migration compatibility
        JSONB,
        nullable=True,
        comment="Additional event data (sanitised — no PII beyond what is necessary)",
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AuditEvent {self.event_type!r} "
            f"actor={self.actor_email!r} at={self.occurred_at}>"
        )
