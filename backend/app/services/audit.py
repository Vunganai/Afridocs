"""
Audit logging service.
Writes immutable AuditEvent records for all significant actions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import AuditEvent

logger = structlog.get_logger(__name__)


class AuditService:
    """
    Writes audit events to the database.
    All writes are append-only — no updates or deletes.
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def log(
        self,
        event_type: str,
        tenant_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        actor_email: str | None = None,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=uuid.uuid4(),
            occurred_at=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._db.add(event)
        # Note: caller is responsible for commit via the session dependency.

        logger.info(
            "audit_event",
            event_type=event_type,
            tenant_id=str(tenant_id) if tenant_id else None,
            actor_email=actor_email,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
        )
        return event


# ── Standard event type constants ─────────────────────────────────────────

class AuditEventType:
    # Auth
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

    # Tenant / User management
    TENANT_CREATED = "tenant.created"
    USER_CREATED = "user.created"
    USER_ROLE_CHANGED = "user.role_changed"

    # Documents
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSING_STARTED = "document.processing_started"
    DOCUMENT_EXTRACTED = "document.extracted"
    DOCUMENT_REVIEW_REQUIRED = "document.review_required"
    DOCUMENT_CORRECTED = "document.corrected"
    DOCUMENT_APPROVED = "document.approved"
    DOCUMENT_REJECTED = "document.rejected"
    DOCUMENT_DUPLICATE_DETECTED = "document.duplicate_detected"
    DOCUMENT_EXPORTED = "document.exported"
