"""
Post-OCR normalisation for invoice text and extracted fields.
Deterministic — no external service calls.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
CURRENCY_CODE_RE = re.compile(r"\b(USD|EUR|GBP|ZAR|KES|NGN|GHS|ZMW|BWP|MZN|TZS|UGX|RWF|ETB|MWK)\b", re.IGNORECASE)
AMOUNT_DUE_RE = re.compile(
    r"(?:amount\s+due|total)\s*[:.]?\s*([€£$R]|ZAR|USD|EUR|GBP)?\s*([\d][\d,]*\.?\d*)\s*(USD|EUR|GBP|ZAR)?",
    re.IGNORECASE,
)
SYMBOL_TO_CODE = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "R": "ZAR",
}


def clean_ocr_text(text: str | None) -> str:
    """Strip control characters (including NUL) and collapse odd whitespace."""
    if not text:
        return ""
    cleaned = CONTROL_CHARS.sub("", text)
    cleaned = cleaned.replace("\u0000", "")
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def looks_like_email(value: str | None) -> bool:
    if not value:
        return False
    return bool(EMAIL_RE.fullmatch(value.strip()))


def extract_first_email(text: str) -> str | None:
    match = EMAIL_RE.search(text or "")
    return match.group(0) if match else None


def detect_currency(text: str, current: str | None = None) -> tuple[str | None, float]:
    """
    Prefer an explicit ISO code next to Amount due / Total (e.g. '$6.90 USD').
    Do not treat South African VAT wording as ZAR when USD/EUR is stated.
    """
    cleaned = clean_ocr_text(text)
    amount_due = AMOUNT_DUE_RE.search(cleaned)
    if amount_due:
        symbol, _amount, trailing_code = amount_due.groups()
        code = (trailing_code or SYMBOL_TO_CODE.get((symbol or "").strip(), "") or "").upper()
        if code:
            return code, 0.95

    codes = [m.upper() for m in CURRENCY_CODE_RE.findall(cleaned)]
    # Ignore ZAR if a hard-currency code also appears (VAT-SA invoices billed in USD)
    non_zar = [c for c in codes if c != "ZAR"]
    if non_zar:
        return non_zar[0], 0.9
    if codes:
        return codes[0], 0.75
    if current:
        return current.upper(), 0.4
    return None, 0.0


def normalise_amount(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip().replace(",", "").replace(" ", "")
    raw = re.sub(r"[^\d.\-]", "", raw)
    if not raw:
        return None
    try:
        return str(Decimal(raw))
    except InvalidOperation:
        return None


def apply_field_heuristics(fields: dict[str, dict], raw_text: str) -> dict[str, dict]:
    """Fix common OCR / model mapping mistakes in-place (returns the same dict)."""
    text = clean_ocr_text(raw_text)

    # Invoice number: strip leftover NUL / odd separators
    inv = fields.get("invoice_number", {})
    if inv.get("value"):
        inv["value"] = CONTROL_CHARS.sub("-", str(inv["value"])).replace("\u0000", "-")
        inv["value"] = re.sub(r"-+", "-", inv["value"]).strip("- ")

    # Currency from document wording, not default ZAR
    detected, conf = detect_currency(text, fields.get("currency", {}).get("value"))
    if detected:
        existing = (fields.get("currency", {}).get("value") or "").upper()
        if existing != detected:
            fields["currency"] = {"value": detected, "confidence": conf}

    # Amounts: numeric-only
    for name in ("total_amount", "vat_amount", "subtotal"):
        if name in fields and fields[name].get("value") is not None:
            normalised = normalise_amount(str(fields[name]["value"]))
            if normalised is not None:
                fields[name]["value"] = normalised

    # Email vs address: Azure often maps VendorAddress onto supplier_email
    email_field = fields.get("supplier_email", {})
    email_val = email_field.get("value")
    if email_val and not looks_like_email(str(email_val)):
        fields["supplier_address"] = {
            "value": str(email_val).strip(),
            "confidence": email_field.get("confidence") or 0.5,
        }
        found = extract_first_email(text)
        if found:
            fields["supplier_email"] = {"value": found, "confidence": 0.92}
        else:
            fields["supplier_email"] = {"value": None, "confidence": 0.0}

    if not fields.get("supplier_email", {}).get("value"):
        found = extract_first_email(text)
        if found:
            # Prefer the supplier block email (first occurrence is usually vendor)
            fields["supplier_email"] = {"value": found, "confidence": 0.85}

    return fields
