"""
Unit tests for the invoice validator — no external calls needed.
"""

import pytest

from app.services.ai.validator import InvoiceValidator


@pytest.fixture
def validator():
    return InvoiceValidator()


def _field(value, confidence=0.95):
    return {"value": value, "confidence": confidence}


def test_valid_invoice_passes(validator):
    fields = {
        "invoice_number": _field("INV-001"),
        "supplier_name": _field("Acme (Pty) Ltd"),
        "total_amount": _field("1150.00"),
        "currency": _field("ZAR"),
    }
    report = validator.validate(fields)
    assert not report.has_errors
    assert not report.should_route_to_review


def test_missing_required_field_fails(validator):
    fields = {
        "invoice_number": _field("INV-001"),
        "supplier_name": _field("Acme"),
        # total_amount missing
        "currency": _field("ZAR"),
    }
    report = validator.validate(fields)
    assert report.has_errors
    assert report.should_route_to_review
    error_fields = [r.field_name for r in report.results if r.status == "invalid"]
    assert "total_amount" in error_fields


def test_zero_amount_fails(validator):
    fields = {
        "invoice_number": _field("INV-002"),
        "supplier_name": _field("Acme"),
        "total_amount": _field("0.00"),
        "currency": _field("ZAR"),
    }
    report = validator.validate(fields)
    assert report.has_errors


def test_low_confidence_routes_to_review(validator):
    fields = {
        "invoice_number": _field("INV-003", confidence=0.50),  # low confidence
        "supplier_name": _field("Acme"),
        "total_amount": _field("500.00"),
        "currency": _field("ZAR"),
    }
    report = validator.validate(fields)
    assert report.should_route_to_review
    warning_fields = [r.field_name for r in report.results if r.status == "warning"]
    assert "invoice_number" in warning_fields


def test_invalid_vat_produces_warning(validator):
    fields = {
        "invoice_number": _field("INV-004"),
        "supplier_name": _field("Acme"),
        "total_amount": _field("1000.00"),
        "currency": _field("ZAR"),
        "supplier_vat_number": _field("12345"),  # too short
    }
    report = validator.validate(fields)
    warning_fields = [r.field_name for r in report.results if r.status == "warning"]
    assert "supplier_vat_number" in warning_fields


def test_future_invoice_date_produces_warning(validator):
    from datetime import date, timedelta
    future_date = (date.today() + timedelta(days=30)).isoformat()
    fields = {
        "invoice_number": _field("INV-005"),
        "supplier_name": _field("Acme"),
        "total_amount": _field("500.00"),
        "currency": _field("ZAR"),
        "invoice_date": _field(future_date),
    }
    report = validator.validate(fields)
    warning_fields = [r.field_name for r in report.results if r.status == "warning"]
    assert "invoice_date" in warning_fields


def test_health_endpoint(client):
    pass  # Integration test — handled in integration tests
