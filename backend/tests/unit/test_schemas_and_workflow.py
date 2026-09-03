"""
Unit tests for Pydantic schema serialization (camelCase conversion)
and workflow action validation.
"""

from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.schemas.common import CamelModel
from app.schemas.document import (
    DocumentListItem,
    DocumentDetail,
    ExtractedFieldSchema,
    ExtractedFieldCorrection,
    DocumentCorrectionsRequest,
    WorkflowActionRequest,
)
from app.api.v1.endpoints.dashboard import DashboardMetrics, DocumentStatusCount


def test_camel_model_alias_generator():
    """Verify CamelModel converts snake_case field names to camelCase on serialization."""
    class SampleModel(CamelModel):
        user_first_name: str
        is_organization_admin: bool
        total_invoices_count: int

    sample = SampleModel(
        user_first_name="Vunganai",
        is_organization_admin=True,
        total_invoices_count=42,
    )
    dumped = sample.model_dump(by_alias=True)
    assert "userFirstName" in dumped
    assert "isOrganizationAdmin" in dumped
    assert "totalInvoicesCount" in dumped
    assert dumped["userFirstName"] == "Vunganai"


def test_extracted_field_serialization():
    """Verify ExtractedFieldSchema serializes attributes to camelCase for the frontend."""
    ef = ExtractedFieldSchema(
        id=uuid4(),
        field_name="total_amount",
        field_value="1500.00",
        confidence_score=0.96,
        was_corrected=True,
        corrected_value="1550.00",
        validation_status="valid",
        validation_message=None,
        effective_value="1550.00",
    )
    dumped = ef.model_dump(by_alias=True)
    assert dumped["fieldName"] == "total_amount"
    assert dumped["fieldValue"] == "1500.00"
    assert dumped["confidenceScore"] == 0.96
    assert dumped["wasCorrected"] is True
    assert dumped["correctedValue"] == "1550.00"
    assert dumped["validationStatus"] == "valid"
    assert dumped["effectiveValue"] == "1550.00"


def test_document_detail_extracted_fields_key():
    """Verify DocumentDetail serializes 'extracted_fields' as 'extractedFields' to prevent frontend crash."""
    now = datetime.now(timezone.utc)
    doc = DocumentDetail(
        id=uuid4(),
        original_filename="sample_invoice.pdf",
        document_type="invoice",
        status="review_required",
        ingestion_channel="upload",
        invoice_number="INV-2024-001",
        invoice_date=date(2024, 8, 15),
        supplier_name="Atlas Supplies",
        total_amount=Decimal("1550.00"),
        currency="ZAR",
        is_duplicate=False,
        has_validation_warnings=True,
        created_at=now,
        updated_at=now,
        file_size_bytes=45000,
        mime_type="application/pdf",
        classification_confidence=0.98,
        due_date=date(2024, 9, 15),
        supplier_vat_number="ZA123456",
        vat_amount=Decimal("202.17"),
        extracted_data=None,
        processing_error=None,
        extracted_fields=[],
        uploaded_by_id=None,
        duplicate_of_id=None,
    )
    dumped = doc.model_dump(by_alias=True)
    assert "extractedFields" in dumped
    assert "originalFilename" in dumped
    assert "invoiceNumber" in dumped
    assert "totalAmount" in dumped
    assert "fileSizeBytes" in dumped
    assert "hasValidationWarnings" in dumped


def test_dashboard_metrics_serialization():
    """Verify DashboardMetrics serializes to camelCase matching frontend types."""
    metrics = DashboardMetrics(
        total_documents=15,
        processed_last_7_days=10,
        processed_last_30_days=15,
        pending_review=3,
        approved=11,
        rejected=1,
        duplicates_caught=0,
        status_breakdown=[DocumentStatusCount(status="review_required", count=3)],
    )
    dumped = metrics.model_dump(by_alias=True)
    assert "totalDocuments" in dumped
    assert "processedLast7Days" in dumped
    assert "pendingReview" in dumped
    assert "statusBreakdown" in dumped
    assert dumped["totalDocuments"] == 15
    assert dumped["statusBreakdown"][0]["status"] == "review_required"


def test_workflow_action_request_validation():
    """Verify workflow action only accepts approve or reject, and trims comments."""
    req_approve = WorkflowActionRequest(action="approve", comment="  Verified all numbers  ")
    assert req_approve.action == "approve"
    assert req_approve.comment == "Verified all numbers"

    req_reject = WorkflowActionRequest(action="reject", comment="")
    assert req_reject.action == "reject"

    with pytest.raises(ValidationError):
        WorkflowActionRequest(action="invalid_action")
