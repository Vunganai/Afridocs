"""
Celery task: process_invoice
The core AI pipeline:
  1. Load document from storage
  2. Classify (is this an invoice?)
  3. Extract fields via Azure Document Intelligence
  4. Gap-fill missing fields via GPT-4o
  5. Validate extracted fields
  6. Detect duplicates
  7. Persist results and update document status
  8. Create initial workflow step
"""

from __future__ import annotations

import uuid

import structlog
from celery import Task

from app.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)

# Required fields that must be present for auto-approval (no human review)
REQUIRED_FOR_AUTO_APPROVE = {"invoice_number", "supplier_name", "total_amount", "currency"}


class ProcessInvoiceTask(Task):
    """Base task class that holds lazy-initialised service references."""

    _storage = None
    _doc_intel = None
    _openai = None
    _validator = None

    @property
    def storage(self):
        if self._storage is None:
            from app.services.storage import StorageService
            self._storage = StorageService()
        return self._storage

    @property
    def doc_intel(self):
        if self._doc_intel is None:
            from app.services.ai.document_intelligence import DocumentIntelligenceService
            self._doc_intel = DocumentIntelligenceService()
        return self._doc_intel

    @property
    def openai_svc(self):
        if self._openai is None:
            from app.services.ai.openai_service import OpenAIService
            self._openai = OpenAIService()
        return self._openai

    @property
    def validator(self):
        if self._validator is None:
            from app.services.ai.validator import InvoiceValidator
            self._validator = InvoiceValidator()
        return self._validator


@celery_app.task(
    bind=True,
    base=ProcessInvoiceTask,
    name="app.worker.tasks.process_document.process_invoice",
    max_retries=3,
    default_retry_delay=30,
    queue="documents",
)
def process_invoice(self: ProcessInvoiceTask, document_id: str) -> dict:
    """
    Main invoice processing task.
    Called after upload; receives the document UUID as a string.
    Returns a status summary dict.
    """
    import asyncio
    return asyncio.run(_process_invoice_async(self, document_id))


async def _process_invoice_async(task: ProcessInvoiceTask, document_id: str) -> dict:
    """Async implementation of the processing pipeline."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.core.config import get_settings
    from app.models.document import Document, DocumentStatus, DocumentVersion, ExtractedField
    from app.models.workflow import WorkflowStep
    from app.services.audit import AuditEventType, AuditService

    settings = get_settings()
    doc_uuid = uuid.UUID(document_id)

    # Create a fresh engine per task — avoids event loop conflicts in Celery prefork workers
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"statement_cache_size": 0},
    )
    TaskSession = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    try:
      async with TaskSession() as db:
        # ── Step 0: Load document ────────────────────────────────────────
        result = await db.execute(select(Document).where(Document.id == doc_uuid))
        document = result.scalar_one_or_none()

        if not document:
            logger.error("process_invoice_doc_not_found", document_id=document_id)
            return {"status": "error", "reason": "document_not_found"}

        if document.status != DocumentStatus.PENDING:
            logger.warning(
                "process_invoice_skipped_wrong_status",
                document_id=document_id,
                status=document.status,
            )
            return {"status": "skipped", "reason": f"unexpected_status:{document.status}"}

        # Mark as processing
        document.status = DocumentStatus.PROCESSING
        await db.commit()

        from app.services.processing_progress import set_progress

        set_progress(
            document_id,
            stage="reading",
            percent=15,
            message="Loading the invoice file...",
            status=DocumentStatus.PROCESSING,
        )

        audit = AuditService(db)

        try:
            # ── Step 1: Read file from storage ───────────────────────────
            logger.info("process_invoice_start", document_id=document_id)
            file_bytes = await task.storage.read(document.storage_path)

            set_progress(
                document_id,
                stage="ocr",
                percent=30,
                message="Reading the invoice with OCR...",
                status=DocumentStatus.PROCESSING,
            )

            # ── Step 2: Classify document ────────────────────────────────
            # Extract raw text first for classification
            extraction_result = task.doc_intel.analyze_invoice(
                file_bytes, document.mime_type
            )
            from app.services.ai.normalizer import apply_field_heuristics, clean_ocr_text

            raw_text = clean_ocr_text(
                getattr(extraction_result, "content", None) or _build_raw_text(extraction_result.fields)
            )
            apply_field_heuristics(extraction_result.fields, raw_text)

            set_progress(
                document_id,
                stage="classify",
                percent=48,
                message="Classifying the document...",
                status=DocumentStatus.PROCESSING,
            )
            classification = task.openai_svc.classify_document(raw_text)
            doc_type = classification.get("document_type", "other")
            class_confidence = classification.get("confidence", 0.0)

            document.classification_confidence = class_confidence

            if doc_type != "invoice":
                # Not an invoice — route to review for human decision
                document.status = DocumentStatus.REVIEW_REQUIRED
                document.processing_error = (
                    f"Document classified as '{doc_type}' "
                    f"(confidence {class_confidence:.0%}). Expected an invoice."
                )
                await db.commit()
                set_progress(
                    document_id,
                    stage="complete",
                    percent=100,
                    message="Not classified as an invoice — sent to review.",
                    status=DocumentStatus.REVIEW_REQUIRED,
                )
                logger.warning(
                    "process_invoice_wrong_type",
                    document_id=document_id,
                    classified_as=doc_type,
                )
                return {"status": "review_required", "reason": "not_an_invoice"}

            # ── Step 3: Check for duplicates ─────────────────────────────
            invoice_number = (
                extraction_result.fields.get("invoice_number", {}).get("value") or ""
            ).strip()
            supplier_name = (
                extraction_result.fields.get("supplier_name", {}).get("value") or ""
            ).strip()

            if invoice_number and supplier_name:
                dup_result = await db.execute(
                    select(Document).where(
                        Document.tenant_id == document.tenant_id,
                        Document.invoice_number == invoice_number,
                        Document.supplier_name.ilike(supplier_name),
                        Document.id != doc_uuid,
                        Document.is_duplicate.is_(False),
                        Document.deleted_at.is_(None),
                    )
                )
                existing = dup_result.scalar_one_or_none()
                if existing:
                    document.status = DocumentStatus.DUPLICATE
                    document.is_duplicate = True
                    document.duplicate_of_id = existing.id
                    await audit.log(
                        event_type=AuditEventType.DOCUMENT_DUPLICATE_DETECTED,
                        tenant_id=document.tenant_id,
                        resource_type="document",
                        resource_id=doc_uuid,
                        metadata={"duplicate_of": str(existing.id)},
                    )
                    await db.commit()
                    set_progress(
                        document_id,
                        stage="complete",
                        percent=100,
                        message="Duplicate invoice detected.",
                        status=DocumentStatus.DUPLICATE,
                    )
                    logger.warning(
                        "process_invoice_duplicate",
                        document_id=document_id,
                        duplicate_of=str(existing.id),
                    )
                    return {"status": "duplicate", "duplicate_of": str(existing.id)}

            # ── Step 4: Gap-fill missing fields via LLM ───────────────────
            set_progress(
                document_id,
                stage="extract",
                percent=62,
                message="Extracting invoice fields...",
                status=DocumentStatus.PROCESSING,
            )
            missing = [
                name for name in REQUIRED_FOR_AUTO_APPROVE
                if not extraction_result.fields.get(name, {}).get("value")
            ]
            if missing:
                gap_fills = task.openai_svc.fill_extraction_gaps(raw_text, missing)
                for field_name, fill_data in gap_fills.items():
                    if not isinstance(fill_data, dict):
                        continue
                    if field_name not in extraction_result.fields or not extraction_result.fields[field_name].get("value"):
                        extraction_result.fields[field_name] = fill_data

            # ── Step 4b: LLM refine pass (currency, email vs address, totals) ─
            set_progress(
                document_id,
                stage="refine",
                percent=78,
                message="Improving extraction accuracy...",
                status=DocumentStatus.PROCESSING,
            )
            refined = task.openai_svc.refine_extraction(raw_text, extraction_result.fields)
            _merge_refined_fields(extraction_result.fields, refined)
            apply_field_heuristics(extraction_result.fields, raw_text)

            # ── Step 5: Validate ─────────────────────────────────────────
            set_progress(
                document_id,
                stage="validate",
                percent=88,
                message="Validating amounts and business rules...",
                status=DocumentStatus.PROCESSING,
            )
            validation_report = task.validator.validate(
                extraction_result.fields,
                confidence_threshold=settings.extraction_confidence_threshold,
            )

            # ── Step 6: Persist extracted fields ─────────────────────────
            set_progress(
                document_id,
                stage="save",
                percent=94,
                message="Saving extracted fields...",
                status=DocumentStatus.PROCESSING,
            )
            # Delete any previous extraction results
            prev = await db.execute(
                select(ExtractedField).where(ExtractedField.document_id == doc_uuid)
            )
            for ef in prev.scalars():
                await db.delete(ef)

            for field_name, field_data in extraction_result.fields.items():
                val_result = next(
                    (r for r in validation_report.results if r.field_name == field_name),
                    None,
                )
                ef = ExtractedField(
                    id=uuid.uuid4(),
                    document_id=doc_uuid,
                    field_name=field_name,
                    field_value=(
                        field_data.get("value")
                        if not isinstance(field_data.get("value"), list)
                        else str(field_data.get("value"))
                    ),
                    confidence_score=field_data.get("confidence"),
                    validation_status=val_result.status if val_result else "skipped",
                    validation_message=val_result.message if val_result else None,
                )
                db.add(ef)

            # ── Step 7: Update document with denormalised fields ──────────
            fields = extraction_result.fields
            document.invoice_number = _field_val(fields, "invoice_number")
            document.supplier_name = _field_val(fields, "supplier_name")
            document.supplier_vat_number = _field_val(fields, "supplier_vat_number")
            document.total_amount = _decimal_val(fields, "total_amount")
            document.vat_amount = _decimal_val(fields, "vat_amount")
            document.currency = (_field_val(fields, "currency") or "ZAR").upper()

            inv_date = _field_val(fields, "invoice_date")
            due_date_val = _field_val(fields, "due_date")
            from app.services.ai.validator import InvoiceValidator
            document.invoice_date = InvoiceValidator._parse_date(inv_date) if inv_date else None
            document.due_date = InvoiceValidator._parse_date(due_date_val) if due_date_val else None

            document.extracted_data = extraction_result.to_dict()
            document.has_validation_warnings = validation_report.has_warnings

            # ── Step 8: Set final status ──────────────────────────────────
            all_required_present = all(
                _field_val(fields, f) for f in REQUIRED_FOR_AUTO_APPROVE
            )
            all_high_confidence = all(
                (fields.get(f, {}).get("confidence") or 0.0)
                >= settings.auto_approve_confidence_threshold
                for f in REQUIRED_FOR_AUTO_APPROVE
            )

            if (
                validation_report.should_route_to_review
                or not all_required_present
                or not all_high_confidence
            ):
                document.status = DocumentStatus.REVIEW_REQUIRED
                await audit.log(
                    event_type=AuditEventType.DOCUMENT_REVIEW_REQUIRED,
                    tenant_id=document.tenant_id,
                    resource_type="document",
                    resource_id=doc_uuid,
                    metadata={
                        "has_errors": validation_report.has_errors,
                        "has_warnings": validation_report.has_warnings,
                        "all_high_confidence": all_high_confidence,
                    },
                )
                # Create workflow step 1 (review)
                ws = WorkflowStep(
                    id=uuid.uuid4(),
                    document_id=doc_uuid,
                    tenant_id=document.tenant_id,
                    step_number=1,
                    step_type="review",
                    status="pending",
                )
                db.add(ws)
            else:
                document.status = DocumentStatus.EXTRACTED
                await audit.log(
                    event_type=AuditEventType.DOCUMENT_EXTRACTED,
                    tenant_id=document.tenant_id,
                    resource_type="document",
                    resource_id=doc_uuid,
                )
                # Create workflow step 1 (approve) — still needs approval
                ws = WorkflowStep(
                    id=uuid.uuid4(),
                    document_id=doc_uuid,
                    tenant_id=document.tenant_id,
                    step_number=1,
                    step_type="approve",
                    status="pending",
                )
                db.add(ws)

            # ── Step 9: Save a version snapshot ───────────────────────────
            version = DocumentVersion(
                id=uuid.uuid4(),
                document_id=doc_uuid,
                version_number=1,
                snapshot=extraction_result.to_dict(),
                change_reason="initial_extraction",
            )
            db.add(version)

            await db.commit()

            set_progress(
                document_id,
                stage="complete",
                percent=100,
                message="Processing complete.",
                status=document.status,
            )

            logger.info(
                "process_invoice_complete",
                document_id=document_id,
                status=document.status,
                invoice_number=document.invoice_number,
                total_amount=str(document.total_amount),
            )

            return {
                "status": document.status,
                "invoice_number": document.invoice_number,
                "total_amount": str(document.total_amount),
                "has_warnings": validation_report.has_warnings,
            }

        except Exception as exc:
            logger.exception("process_invoice_failed", document_id=document_id, error=str(exc))
            document.status = DocumentStatus.FAILED
            document.processing_error = str(exc)
            await db.commit()
            set_progress(
                document_id,
                stage="save",
                percent=100,
                message=str(exc),
                status=DocumentStatus.FAILED,
                error=str(exc),
            )

            # Retry with exponential backoff (max 3 attempts)
            raise task.retry(exc=exc)
    finally:
        await engine.dispose()


def _merge_refined_fields(fields: dict, refined: dict) -> None:
    """Merge LLM refine output when it fills a gap or has equal/higher confidence."""
    if not refined:
        return
    for name, data in refined.items():
        if not isinstance(data, dict) or name == "line_items":
            continue
        value = data.get("value")
        if value in (None, "", "null"):
            continue
        try:
            conf = float(data.get("confidence") or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        existing = fields.get(name) or {}
        existing_val = existing.get("value")
        existing_conf = float(existing.get("confidence") or 0.0)
        if not existing_val or conf >= existing_conf:
            fields[name] = {"value": value, "confidence": conf}


def _field_val(fields: dict, name: str) -> str | None:
    return fields.get(name, {}).get("value") or None


def _decimal_val(fields: dict, name: str):
    from decimal import Decimal, InvalidOperation
    val = _field_val(fields, name)
    if not val:
        return None
    try:
        return Decimal(str(val))
    except InvalidOperation:
        return None


def _build_raw_text(fields: dict) -> str:
    """Build a flat text representation of extracted fields for LLM classification."""
    parts = []
    for name, data in fields.items():
        value = data.get("value")
        if value and not isinstance(value, list):
            parts.append(f"{name}: {value}")
    return "\n".join(parts)
