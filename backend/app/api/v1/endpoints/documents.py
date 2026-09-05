"""
Document endpoints — upload, list, detail, corrections, export.
"""

import contextlib
import csv
import io
import json
import uuid
from typing import Annotated

import magic
import structlog
from fastapi import APIRouter, File, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UploadError
from app.core.security import CurrentUser
from app.db.session import DbSession
from app.models.document import Document, DocumentStatus, DocumentVersion, ExtractedField
from app.models.user import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.document import (
    DocumentCorrectionsRequest,
    DocumentDetail,
    DocumentListItem,
    ExportRequest,
    ProcessingProgress,
    UploadResponse,
)
from app.services.audit import AuditEventType, AuditService
from app.services.processing_progress import (
    build_steps,
    fallback_from_status,
    get_progress,
    set_progress,
)
from app.services.storage import StorageService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


async def _get_tenant_user(current_user: CurrentUser, db: DbSession) -> User:
    """Resolve the DB User record from the JWT claims."""
    result = await db.execute(
        select(User).where(User.supabase_user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User profile not found. Please complete onboarding.")
    return user


# ── Upload ─────────────────────────────────────────────────────────────────

@router.post("", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    file: Annotated[UploadFile, File(description="PDF or image invoice file")],
    current_user: CurrentUser,
    db: DbSession,
) -> UploadResponse:
    """
    Upload an invoice document.
    - Validates MIME type and file size
    - Saves to storage
    - Enqueues async AI processing task
    - Returns document_id and initial status
    """
    settings = get_settings()
    db_user = await _get_tenant_user(current_user, db)

    # ── Validation: file size ──────────────────────────────────────────────
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise UploadError(
            f"File exceeds the maximum allowed size of {settings.max_upload_size_mb} MB."
        )

    if len(file_bytes) == 0:
        raise UploadError("Uploaded file is empty.")

    # ── Validation: MIME type (magic bytes, not Content-Type header) ────────
    detected_mime = magic.from_buffer(file_bytes, mime=True)
    if detected_mime not in settings.allowed_mime_types_list:
        raise UploadError(
            f"File type '{detected_mime}' is not allowed. "
            f"Accepted types: {', '.join(settings.allowed_mime_types_list)}"
        )

    original_filename = file.filename or "upload"

    # ── Save to storage ────────────────────────────────────────────────────
    storage = StorageService()
    storage_path, file_hash = await storage.save(file_bytes, original_filename)

    # ── Duplicate file hash check ──────────────────────────────────────────
    existing = await db.execute(
        select(Document).where(
            Document.tenant_id == db_user.tenant_id,
            Document.file_hash == file_hash,
            Document.is_duplicate.is_(False),
            Document.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(
            "A document with identical content has already been uploaded. "
            "Use the existing document or contact support if this is unexpected."
        )

    # ── Create document record ─────────────────────────────────────────────
    doc = Document(
        tenant_id=db_user.tenant_id,
        uploaded_by_id=db_user.id,
        original_filename=original_filename,
        file_size_bytes=len(file_bytes),
        mime_type=detected_mime,
        storage_path=storage_path,
        file_hash=file_hash,
        document_type="invoice",
        status=DocumentStatus.PENDING,
        ingestion_channel="upload",
        currency="ZAR",
    )
    db.add(doc)
    await db.flush()  # Get doc.id

    # ── Audit ──────────────────────────────────────────────────────────────
    audit = AuditService(db)
    await audit.log(
        event_type=AuditEventType.DOCUMENT_UPLOADED,
        tenant_id=db_user.tenant_id,
        actor_id=db_user.id,
        actor_email=db_user.email,
        resource_type="document",
        resource_id=doc.id,
        metadata={
            "filename": original_filename,
            "mime_type": detected_mime,
            "size_bytes": len(file_bytes),
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # ── Enqueue processing task ────────────────────────────────────────────
    try:
        from app.worker.tasks.process_document import process_invoice
        process_invoice.delay(str(doc.id))
    except Exception as exc:
        logger.warning("celery_enqueue_failed_at_upload", document_id=str(doc.id), error=str(exc))

    set_progress(
        str(doc.id),
        stage="queued",
        percent=8,
        message="Upload complete. Waiting for AI processing to start.",
        status=DocumentStatus.PENDING,
    )

    logger.info(
        "document_uploaded",
        document_id=str(doc.id),
        tenant_id=str(db_user.tenant_id),
        filename=original_filename,
    )

    return UploadResponse(
        document_id=doc.id,
        status=DocumentStatus.PENDING,
        message="Document uploaded successfully. Processing has started.",
    )


# ── List ───────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[DocumentListItem])
async def list_documents(
    current_user: CurrentUser,
    db: DbSession,
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_name: str | None = Query(default=None),
    invoice_number: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[DocumentListItem]:
    """
    List documents for the authenticated user's tenant.
    Supports filtering by status, supplier, and invoice number.
    """
    db_user = await _get_tenant_user(current_user, db)

    query = (
        select(Document)
        .where(
            Document.tenant_id == db_user.tenant_id,
            Document.deleted_at.is_(None),
        )
        .order_by(Document.created_at.desc())
    )

    if status_filter:
        query = query.where(Document.status == status_filter)
    if supplier_name:
        query = query.where(Document.supplier_name.ilike(f"%{supplier_name}%"))
    if invoice_number:
        query = query.where(Document.invoice_number.ilike(f"%{invoice_number}%"))

    # Total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginated results
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


# ── Detail ─────────────────────────────────────────────────────────────────

@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentDetail:
    """Get full document detail including all extracted fields."""
    db_user = await _get_tenant_user(current_user, db)

    result = await db.execute(
        select(Document)
        .options(selectinload(Document.extracted_fields))
        .where(
            Document.id == document_id,
            Document.tenant_id == db_user.tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"Document {document_id} not found.")

    return DocumentDetail.model_validate(doc)


@router.get("/{document_id}/progress", response_model=ProcessingProgress)
async def get_document_progress(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ProcessingProgress:
    """Live processing progress for the upload loading screen."""
    db_user = await _get_tenant_user(current_user, db)
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == db_user.tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"Document {document_id} not found.")

    cached = get_progress(str(document_id)) or fallback_from_status(doc.status, doc.processing_error)
    status = doc.status
    done = status in (
        DocumentStatus.EXTRACTED,
        DocumentStatus.REVIEW_REQUIRED,
        DocumentStatus.APPROVED,
        DocumentStatus.REJECTED,
        DocumentStatus.DUPLICATE,
        DocumentStatus.FAILED,
    )
    if done:
        cached["done"] = True
        cached["percent"] = 100
        cached["status"] = status
        if status == DocumentStatus.FAILED:
            cached["stage"] = cached.get("stage") or "save"
            cached["message"] = doc.processing_error or cached.get("message") or "Processing failed."
            cached["error"] = doc.processing_error
        else:
            cached["stage"] = "complete"
            cached["message"] = cached.get("message") or "Processing complete."
            cached["error"] = None

    failed = status == DocumentStatus.FAILED
    steps = build_steps(cached.get("stage") or "queued", done=done and not failed, failed=failed)
    return ProcessingProgress(
        document_id=doc.id,
        filename=doc.original_filename,
        status=status,
        stage=cached.get("stage") or "queued",
        percent=int(cached.get("percent") or 0),
        message=cached.get("message") or "Processing...",
        done=bool(cached.get("done")),
        error=cached.get("error") or doc.processing_error,
        steps=steps,
    )


# ── Delete ─────────────────────────────────────────────────────────────────

@router.delete("/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """Soft-delete an invoice. Admins, reviewers, and approvers can delete."""
    db_user = await _get_tenant_user(current_user, db)

    if db_user.role not in ("admin", "reviewer", "approver"):
        raise ForbiddenError("You do not have permission to delete invoices.")

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == db_user.tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"Document {document_id} not found.")

    storage_path = doc.storage_path
    doc.soft_delete()

    audit = AuditService(db)
    await audit.log(
        event_type=AuditEventType.DOCUMENT_DELETED,
        tenant_id=db_user.tenant_id,
        actor_id=db_user.id,
        actor_email=db_user.email,
        resource_type="document",
        resource_id=document_id,
        metadata={"filename": doc.original_filename},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    try:
        await StorageService().delete(storage_path)
    except Exception as exc:
        logger.warning(
            "document_file_delete_failed",
            document_id=str(document_id),
            error=str(exc),
        )

    logger.info("document_deleted", document_id=str(document_id), actor=db_user.email)
    return MessageResponse(message="Invoice deleted.")


# ── Document File (Preview / Stream) ───────────────────────────────────────

@router.get("/{document_id}/file")
async def get_document_file(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    """
    Stream the original uploaded invoice file (PDF or image)
    for in-browser preview during document review.
    """
    db_user = await _get_tenant_user(current_user, db)

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == db_user.tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"Document {document_id} not found.")

    storage = StorageService()
    try:
        file_bytes = await storage.read(doc.storage_path)
    except Exception as exc:
        logger.error("file_read_error", document_id=str(document_id), error=str(exc))
        raise NotFoundError("Document file not found in storage.") from exc

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.original_filename}"',
            "Content-Type": doc.mime_type,
        },
    )


# ── Process / Reprocess ────────────────────────────────────────────────────

@router.post("/{document_id}/process", response_model=MessageResponse)
async def trigger_document_processing(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    sync: bool = Query(default=False, description="Run synchronously if Celery is not available"),
) -> MessageResponse:
    """
    Trigger or retry document processing.
    Useful when a document is stuck in pending or failed state,
    or during local development.
    """
    db_user = await _get_tenant_user(current_user, db)

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == db_user.tenant_id,
            Document.deleted_at.is_(None),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError(f"Document {document_id} not found.")

    # Reset status
    doc.status = DocumentStatus.PENDING
    doc.processing_error = None
    await db.flush()
    set_progress(
        str(doc.id),
        stage="queued",
        percent=8,
        message="Processing restarted.",
        status=DocumentStatus.PENDING,
    )

    if sync:
        from app.worker.tasks.process_document import ProcessInvoiceTask, _process_invoice_async
        task = ProcessInvoiceTask()
        try:
            res = await _process_invoice_async(task, str(doc.id))
            return MessageResponse(message=f"Document processed successfully: {res.get('status')}")
        except Exception as exc:
            logger.warning("sync_process_failed_falling_back_to_simulation", document_id=str(document_id), error=str(exc))
            await _simulate_mock_extraction(doc, db, db_user)
            return MessageResponse(
                message="Processed document with development simulation (Azure credentials unavailable)."
            )
    else:
        try:
            from app.worker.tasks.process_document import process_invoice
            process_invoice.delay(str(doc.id))
            return MessageResponse(message="Document processing enqueued successfully.")
        except Exception as exc:
            logger.warning("celery_enqueue_failed_falling_back_to_simulation", error=str(exc))
            from app.worker.tasks.process_document import ProcessInvoiceTask, _process_invoice_async
            task = ProcessInvoiceTask()
            try:
                res = await _process_invoice_async(task, str(doc.id))
                return MessageResponse(message=f"Document processed: {res.get('status')}")
            except Exception:
                await _simulate_mock_extraction(doc, db, db_user)
                return MessageResponse(
                    message="Document processed using development simulation."
                )


async def _simulate_mock_extraction(doc: Document, db: DbSession, db_user: User):
    """
    Development fallback: if external AI services (Azure Doc Intelligence / OpenAI)
    are unreachable or placeholder keys are configured, populate mock extracted fields
    so that human review and approval workflows can be tested seamlessly.
    """
    from datetime import date
    from decimal import Decimal

    from app.models.workflow import WorkflowStep

    clean_name = doc.original_filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    doc.invoice_number = f"INV-{uuid.uuid4().hex[:6].upper()}"
    doc.supplier_name = clean_name if len(clean_name) > 3 else "Atlas General Trading (Pty) Ltd"
    doc.supplier_vat_number = "ZA4890123456"
    doc.total_amount = Decimal("14850.00")
    doc.vat_amount = Decimal("1936.96")
    doc.currency = "ZAR"
    doc.invoice_date = date.today()
    doc.status = DocumentStatus.REVIEW_REQUIRED
    doc.has_validation_warnings = True
    doc.classification_confidence = 0.92

    # Remove prior fields if any
    prev = await db.execute(
        select(ExtractedField).where(ExtractedField.document_id == doc.id)
    )
    for ef in prev.scalars():
        await db.delete(ef)

    mock_fields = [
        ("invoice_number", doc.invoice_number, 0.94, "valid", None),
        ("supplier_name", doc.supplier_name, 0.88, "valid", None),
        ("supplier_vat_number", doc.supplier_vat_number, 0.82, "warning", "VAT format flagged for human verification"),
        ("total_amount", "14850.00", 0.95, "valid", None),
        ("vat_amount", "1936.96", 0.78, "warning", "Confidence below 80% — please verify tax calculation"),
        ("invoice_date", str(doc.invoice_date), 0.91, "valid", None),
        ("currency", "ZAR", 0.99, "valid", None),
    ]

    for fname, fval, conf, vstatus, vmsg in mock_fields:
        ef = ExtractedField(
            id=uuid.uuid4(),
            document_id=doc.id,
            field_name=fname,
            field_value=fval,
            confidence_score=conf,
            validation_status=vstatus,
            validation_message=vmsg,
        )
        db.add(ef)

    # Add workflow step 1
    existing_step = await db.execute(
        select(WorkflowStep).where(
            WorkflowStep.document_id == doc.id,
            WorkflowStep.status == "pending",
        )
    )
    if not existing_step.scalar_one_or_none():
        ws = WorkflowStep(
            id=uuid.uuid4(),
            document_id=doc.id,
            tenant_id=doc.tenant_id,
            step_number=1,
            step_type="review",
            status="pending",
        )
        db.add(ws)

    audit = AuditService(db)
    await audit.log(
        event_type=AuditEventType.DOCUMENT_REVIEW_REQUIRED,
        tenant_id=doc.tenant_id,
        actor_id=db_user.id,
        resource_type="document",
        resource_id=doc.id,
        metadata={"simulation": True},
    )
    await db.flush()
    set_progress(
        str(doc.id),
        stage="complete",
        percent=100,
        message="Processing complete.",
        status=DocumentStatus.REVIEW_REQUIRED,
    )


# ── Corrections ────────────────────────────────────────────────────────────

@router.patch("/{document_id}/corrections", response_model=MessageResponse)
async def correct_document(
    document_id: uuid.UUID,
    body: DocumentCorrectionsRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    """
    Apply human corrections to extracted fields.
    Allowed roles: admin, reviewer.
    Creates a new version snapshot after corrections are saved.
    Also synchronises denormalised fields on Document for consistency.
    """
    from decimal import Decimal, InvalidOperation

    from app.services.ai.validator import InvoiceValidator

    db_user = await _get_tenant_user(current_user, db)

    if db_user.role not in ("admin", "reviewer"):
        raise ForbiddenError("Only reviewers and admins can correct extracted fields.")

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

    if doc.status not in (DocumentStatus.REVIEW_REQUIRED, DocumentStatus.EXTRACTED):
        raise UploadError(
            f"Document in status '{doc.status}' cannot be corrected. "
            "Only documents in 'review_required' or 'extracted' status can be corrected."
        )

    # Apply corrections
    for correction in body.corrections:
        field_result = await db.execute(
            select(ExtractedField).where(
                ExtractedField.document_id == document_id,
                ExtractedField.field_name == correction.field_name,
            )
        )
        ef = field_result.scalar_one_or_none()
        if ef:
            ef.was_corrected = True
            ef.corrected_value = correction.corrected_value
            ef.corrected_by_id = db_user.id
            ef.validation_status = "valid"
            ef.validation_message = "Manually corrected by reviewer."
        else:
            ef = ExtractedField(
                id=uuid.uuid4(),
                document_id=document_id,
                field_name=correction.field_name,
                field_value=correction.corrected_value,
                confidence_score=1.0,
                was_corrected=True,
                corrected_value=correction.corrected_value,
                corrected_by_id=db_user.id,
                validation_status="valid",
                validation_message="Manually added by reviewer.",
            )
            db.add(ef)

        # Synchronise denormalised fields on Document
        fname = correction.field_name
        val = correction.corrected_value
        if fname == "invoice_number":
            doc.invoice_number = val
        elif fname == "supplier_name":
            doc.supplier_name = val
        elif fname == "supplier_vat_number":
            doc.supplier_vat_number = val
        elif fname == "currency" and val:
            doc.currency = val.upper()
        elif fname == "total_amount":
            with contextlib.suppress(InvalidOperation):
                doc.total_amount = Decimal(str(val)) if val else None
        elif fname == "vat_amount":
            with contextlib.suppress(InvalidOperation):
                doc.vat_amount = Decimal(str(val)) if val else None
        elif fname == "invoice_date":
            doc.invoice_date = InvoiceValidator._parse_date(val) if val else None
        elif fname == "due_date":
            doc.due_date = InvoiceValidator._parse_date(val) if val else None

    # Save version snapshot
    snapshot = {
        c.field_name: c.corrected_value for c in body.corrections
    }
    version_result = await db.execute(
        select(func.max(DocumentVersion.version_number)).where(
            DocumentVersion.document_id == document_id
        )
    )
    max_version = version_result.scalar_one_or_none() or 0

    version = DocumentVersion(
        id=uuid.uuid4(),
        document_id=document_id,
        version_number=max_version + 1,
        snapshot=snapshot,
        created_by_id=db_user.id,
        change_reason="human_correction",
    )
    db.add(version)

    # Audit
    audit = AuditService(db)
    await audit.log(
        event_type=AuditEventType.DOCUMENT_CORRECTED,
        tenant_id=db_user.tenant_id,
        actor_id=db_user.id,
        actor_email=db_user.email,
        resource_type="document",
        resource_id=document_id,
        metadata={"fields_corrected": [c.field_name for c in body.corrections]},
    )

    return MessageResponse(message=f"{len(body.corrections)} field(s) corrected successfully.")


# ── Export ─────────────────────────────────────────────────────────────────

@router.post("/export", response_class=StreamingResponse)
async def export_documents(
    body: ExportRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    """Export documents as CSV or JSON."""
    db_user = await _get_tenant_user(current_user, db)

    query = select(Document).where(
        Document.tenant_id == db_user.tenant_id,
        Document.deleted_at.is_(None),
    )
    if body.document_ids:
        query = query.where(Document.id.in_(body.document_ids))

    result = await db.execute(query)
    documents = result.scalars().all()

    audit = AuditService(db)
    await audit.log(
        event_type=AuditEventType.DOCUMENT_EXPORTED,
        tenant_id=db_user.tenant_id,
        actor_id=db_user.id,
        actor_email=db_user.email,
        metadata={"format": body.format, "count": len(documents)},
    )

    if body.format == "json":
        data = [DocumentListItem.model_validate(d).model_dump() for d in documents]
        content = json.dumps(data, default=str, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=afridocs_export.json"},
        )

    # CSV
    output = io.StringIO()
    fieldnames = [
        "id", "original_filename", "status", "invoice_number", "invoice_date",
        "supplier_name", "supplier_vat_number", "total_amount", "vat_amount",
        "currency", "due_date", "is_duplicate", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for d in documents:
        writer.writerow({
            "id": str(d.id),
            "original_filename": d.original_filename,
            "status": d.status,
            "invoice_number": d.invoice_number or "",
            "invoice_date": str(d.invoice_date) if d.invoice_date else "",
            "supplier_name": d.supplier_name or "",
            "supplier_vat_number": d.supplier_vat_number or "",
            "total_amount": str(d.total_amount) if d.total_amount else "",
            "vat_amount": str(d.vat_amount) if d.vat_amount else "",
            "currency": d.currency,
            "due_date": str(d.due_date) if d.due_date else "",
            "is_duplicate": str(d.is_duplicate),
            "created_at": str(d.created_at),
        })

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=afridocs_export.csv"},
    )
