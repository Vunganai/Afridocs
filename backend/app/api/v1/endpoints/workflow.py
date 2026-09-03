"""
Workflow endpoints — review queue, approval, rejection.
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.models.workflow import WorkflowStep
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.document import DocumentListItem, WorkflowActionRequest, WorkflowStepSchema
from app.services.audit import AuditEventType, AuditService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/workflow", tags=["Workflow"])


async def _get_tenant_user(current_user: CurrentUser, db: DbSession) -> User:
    result = await db.execute(
        select(User).where(User.supabase_user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User profile not found. Please complete onboarding.")
    return user


# ── Review Queue ───────────────────────────────────────────────────────────

@router.get("/queue", response_model=PaginatedResponse[DocumentListItem])
async def get_review_queue(
    current_user: CurrentUser,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[DocumentListItem]:
    """
    Returns all documents in the tenant's review queue.
    Ordered by creation date (oldest first — FIFO processing).
    Accessible to: admin, reviewer, approver.
    """
    db_user = await _get_tenant_user(current_user, db)

    if db_user.role not in ("admin", "reviewer", "approver"):
        raise ForbiddenError("You do not have access to the review queue.")

    allowed_statuses = [
        DocumentStatus.REVIEW_REQUIRED,
        DocumentStatus.EXTRACTED,
    ]
    if status_filter and status_filter in allowed_statuses:
        target_statuses = [status_filter]
    else:
        target_statuses = allowed_statuses

    from sqlalchemy import func
    query = (
        select(Document)
        .where(
            Document.tenant_id == db_user.tenant_id,
            Document.status.in_(target_statuses),
            Document.deleted_at.is_(None),
        )
        .order_by(Document.created_at.asc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    documents = result.scalars().all()

    return PaginatedResponse(
        items=[DocumentListItem.model_validate(d) for d in documents],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
    )


# ── Take Action ────────────────────────────────────────────────────────────

@router.post("/{document_id}/action", response_model=MessageResponse)
async def take_workflow_action(
    document_id: uuid.UUID,
    body: WorkflowActionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """
    Approve or reject a document.

    - Reviewers (step 1): can approve documents in 'review_required' status.
      Their approval moves the document to 'extracted' and creates step 2.
    - Approvers (step 2) / admins: final approval → 'approved' status.
    - Any authorised user can reject.

    MVP workflow:
      REVIEW_REQUIRED → [reviewer approves] → EXTRACTED → [approver approves] → APPROVED
      Any step → [reject] → REJECTED
    """
    db_user = await _get_tenant_user(current_user, db)

    if db_user.role not in ("admin", "reviewer", "approver"):
        raise ForbiddenError("You do not have permission to take workflow actions.")

    # Load document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == db_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"Document {document_id} not found.")

    if doc.status in (DocumentStatus.APPROVED, DocumentStatus.REJECTED):
        raise ForbiddenError(
            f"Document is already '{doc.status}' and cannot be actioned again."
        )

    if doc.status == DocumentStatus.PENDING or doc.status == DocumentStatus.PROCESSING:
        raise ForbiddenError(
            "Document is still being processed. Please wait for extraction to complete."
        )

    # Get the pending workflow step
    step_result = await db.execute(
        select(WorkflowStep).where(
            WorkflowStep.document_id == document_id,
            WorkflowStep.status == "pending",
        ).order_by(WorkflowStep.step_number.asc())
    )
    pending_step = step_result.scalar_one_or_none()

    if pending_step is None:
        # No pending step — create one now (handles edge cases)
        pending_step = WorkflowStep(
            id=uuid.uuid4(),
            document_id=document_id,
            tenant_id=db_user.tenant_id,
            step_number=1,
            step_type="approve",
            status="pending",
        )
        db.add(pending_step)
        await db.flush()

    now = datetime.now(timezone.utc)

    if body.action == "reject":
        # ── Reject ──────────────────────────────────────────────────────
        pending_step.status = "rejected"
        pending_step.action_taken_by_id = db_user.id
        pending_step.actioned_at = now
        pending_step.comment = body.comment

        doc.status = DocumentStatus.REJECTED

        audit_event = AuditEventType.DOCUMENT_REJECTED
        message = "Document rejected successfully."

    else:
        # ── Approve ─────────────────────────────────────────────────────
        pending_step.status = "approved"
        pending_step.action_taken_by_id = db_user.id
        pending_step.actioned_at = now
        pending_step.comment = body.comment

        if doc.status == DocumentStatus.REVIEW_REQUIRED:
            # Step 1 approval (reviewer clears the review requirement)
            # Move to EXTRACTED and create step 2 for final approval
            doc.status = DocumentStatus.EXTRACTED

            step2 = WorkflowStep(
                id=uuid.uuid4(),
                document_id=document_id,
                tenant_id=db_user.tenant_id,
                step_number=2,
                step_type="approve",
                status="pending",
            )
            db.add(step2)
            audit_event = AuditEventType.DOCUMENT_REVIEW_REQUIRED  # reuse — marks reviewed
            message = "Review approved. Document moved to approval queue."

        else:
            # Step 2 (or direct approval from EXTRACTED)
            # Check role permissions for final approval
            if db_user.role == "reviewer" and db_user.role != "admin":
                raise ForbiddenError(
                    "Reviewers cannot give final approval. "
                    "This document is in the approval queue and requires an Approver or Admin sign-off."
                )

            doc.status = DocumentStatus.APPROVED
            audit_event = AuditEventType.DOCUMENT_APPROVED
            message = "Document approved successfully."

    # Audit
    audit = AuditService(db)
    await audit.log(
        event_type=audit_event,
        tenant_id=db_user.tenant_id,
        actor_id=db_user.id,
        actor_email=db_user.email,
        resource_type="document",
        resource_id=document_id,
        metadata={
            "action": body.action,
            "step_number": pending_step.step_number,
            "comment": body.comment,
        },
    )

    logger.info(
        "workflow_action",
        document_id=str(document_id),
        action=body.action,
        actor=db_user.email,
        new_status=doc.status,
    )

    return MessageResponse(message=message)


# ── Workflow History ───────────────────────────────────────────────────────

@router.get("/{document_id}/steps", response_model=list[WorkflowStepSchema])
async def get_workflow_steps(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> list[WorkflowStepSchema]:
    """Return all workflow steps for a document (approval history)."""
    db_user = await _get_tenant_user(current_user, db)

    # Verify document belongs to tenant
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == db_user.tenant_id,
        )
    )
    if not doc_result.scalar_one_or_none():
        raise NotFoundError(f"Document {document_id} not found.")

    steps_result = await db.execute(
        select(WorkflowStep)
        .where(WorkflowStep.document_id == document_id)
        .order_by(WorkflowStep.step_number.asc())
    )
    steps = steps_result.scalars().all()

    return [WorkflowStepSchema.model_validate(s) for s in steps]
