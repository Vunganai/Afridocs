"""Tests for invoice OCR normalisation and currency / email heuristics."""

from app.services.ai.normalizer import (
    apply_field_heuristics,
    clean_ocr_text,
    detect_currency,
    extract_first_email,
    looks_like_email,
    normalise_amount,
)
from app.services.ai.validator import InvoiceValidator


ELEVENLABS_OCR = """
Invoice number ZD1OSZRA\x000002
Eleven Labs Inc. (@elevenlabs)
169 Madison Avenue #2484
New York, New York 10016
United States
team@elevenlabs.io
ZA VAT 4300323179
Bill to
Vunganai Javangwe
$6.90 USD due July 30, 2026
VAT - South Africa 15% on $6.00 $0.90
(R15.00)
Total $6.90
Amount due $6.90 USD
"""


def test_clean_ocr_text_strips_nuls():
    assert "\x00" not in clean_ocr_text("ZD1OSZRA\x000002")
    assert "ZD1OSZRA0002" in clean_ocr_text("ZD1OSZRA\x000002").replace("-", "")


def test_detect_currency_prefers_amount_due_usd_over_sa_vat():
    code, conf = detect_currency(ELEVENLABS_OCR, current="ZAR")
    assert code == "USD"
    assert conf >= 0.9


def test_email_heuristics_fix_address_mapped_as_email():
    fields = {
        "supplier_email": {
            "value": "169 Madison Avenue #2484New York, New York 10016United States",
            "confidence": 0.86,
        },
        "currency": {"value": "ZAR", "confidence": 0.5},
        "total_amount": {"value": "$6.90", "confidence": 0.98},
    }
    apply_field_heuristics(fields, ELEVENLABS_OCR)
    assert fields["supplier_email"]["value"] == "team@elevenlabs.io"
    assert looks_like_email(fields["supplier_email"]["value"])
    assert "Madison" in (fields.get("supplier_address") or {}).get("value", "")
    assert fields["currency"]["value"] == "USD"
    assert fields["total_amount"]["value"] == "6.90"


def test_extract_first_email():
    assert extract_first_email(ELEVENLABS_OCR) == "team@elevenlabs.io"


def test_normalise_amount():
    assert normalise_amount("$6.90") == "6.90"
    assert normalise_amount("1,250.00") == "1250.00"


def test_validator_flags_total_mismatch():
    report = InvoiceValidator().validate(
        {
            "invoice_number": {"value": "INV-1", "confidence": 0.9},
            "supplier_name": {"value": "Acme", "confidence": 0.9},
            "total_amount": {"value": "10.00", "confidence": 0.9},
            "currency": {"value": "USD", "confidence": 0.9},
            "subtotal": {"value": "6.00", "confidence": 0.9},
            "vat_amount": {"value": "0.90", "confidence": 0.9},
        }
    )
    messages = [r.message or "" for r in report.results]
    assert any("does not match subtotal" in m for m in messages)
    assert report.should_route_to_review
