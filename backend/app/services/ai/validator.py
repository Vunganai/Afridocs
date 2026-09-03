"""
Business rule validator for extracted invoice fields.
Pure Python — no external service calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation


@dataclass
class FieldValidationResult:
    field_name: str
    status: str  # valid | invalid | warning | skipped
    message: str | None = None


@dataclass
class ValidationReport:
    results: list[FieldValidationResult] = field(default_factory=list)
    has_errors: bool = False
    has_warnings: bool = False
    should_route_to_review: bool = False

    def add(self, result: FieldValidationResult) -> None:
        self.results.append(result)
        if result.status == "invalid":
            self.has_errors = True
            self.should_route_to_review = True
        elif result.status == "warning":
            self.has_warnings = True


class InvoiceValidator:
    """
    Validates extracted invoice fields against business rules.
    All rules are deterministic — no AI calls.
    """

    SA_VAT_PATTERN = re.compile(r"^\d{10}$")
    VALID_CURRENCIES = {
        "ZAR", "USD", "EUR", "GBP", "KES", "NGN", "GHS", "ZMW", "BWP",
        "MZN", "TZS", "UGX", "RWF", "ETB", "MWK",
    }
    REQUIRED_FIELDS = {"invoice_number", "supplier_name", "total_amount", "currency"}
    CONFIDENCE_THRESHOLD = 0.80

    def validate(
        self,
        fields: dict[str, dict],
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> ValidationReport:
        report = ValidationReport()

        # Check required fields
        for required in self.REQUIRED_FIELDS:
            field_data = fields.get(required, {})
            value = field_data.get("value")
            confidence = field_data.get("confidence", 0.0)

            if not value:
                report.add(FieldValidationResult(
                    field_name=required,
                    status="invalid",
                    message=f"Required field '{required}' is missing.",
                ))
                continue

            if confidence < confidence_threshold:
                report.add(FieldValidationResult(
                    field_name=required,
                    status="warning",
                    message=(
                        f"Low confidence ({confidence:.0%}) on required field '{required}'. "
                        "Human review recommended."
                    ),
                ))
            else:
                report.add(FieldValidationResult(field_name=required, status="valid"))

        # Validate total_amount > 0
        total_data = fields.get("total_amount", {})
        total_value = total_data.get("value")
        if total_value:
            try:
                total = Decimal(str(total_value))
                if total <= 0:
                    report.add(FieldValidationResult(
                        field_name="total_amount",
                        status="invalid",
                        message="Total amount must be greater than zero.",
                    ))
            except InvalidOperation:
                report.add(FieldValidationResult(
                    field_name="total_amount",
                    status="invalid",
                    message=f"Total amount '{total_value}' is not a valid number.",
                ))

        # Validate currency
        currency_data = fields.get("currency", {})
        currency_value = (currency_data.get("value") or "ZAR").upper().strip()
        if currency_value not in self.VALID_CURRENCIES:
            report.add(FieldValidationResult(
                field_name="currency",
                status="warning",
                message=f"Currency '{currency_value}' is not in the recognised list.",
            ))

        # Validate invoice_date (not unreasonably future-dated)
        date_data = fields.get("invoice_date", {})
        date_value = date_data.get("value")
        if date_value:
            parsed_date = self._parse_date(date_value)
            if parsed_date:
                max_future = date.today() + timedelta(days=7)
                if parsed_date > max_future:
                    report.add(FieldValidationResult(
                        field_name="invoice_date",
                        status="warning",
                        message=f"Invoice date {parsed_date} is more than 7 days in the future.",
                    ))
            else:
                report.add(FieldValidationResult(
                    field_name="invoice_date",
                    status="warning",
                    message=f"Could not parse invoice_date value: '{date_value}'.",
                ))

        # Validate due_date >= invoice_date
        due_data = fields.get("due_date", {})
        due_value = due_data.get("value")
        if due_value and date_value:
            inv_date = self._parse_date(date_value)
            due_date_parsed = self._parse_date(due_value)
            if inv_date and due_date_parsed and due_date_parsed < inv_date:
                report.add(FieldValidationResult(
                    field_name="due_date",
                    status="warning",
                    message="Due date is before invoice date.",
                ))

        # Validate SA VAT number format
        vat_data = fields.get("supplier_vat_number", {})
        vat_value = vat_data.get("value")
        if vat_value:
            clean_vat = re.sub(r"[^0-9]", "", str(vat_value))
            if not self.SA_VAT_PATTERN.match(clean_vat):
                report.add(FieldValidationResult(
                    field_name="supplier_vat_number",
                    status="warning",
                    message=(
                        f"VAT number '{vat_value}' does not match SARS format "
                        "(10 digits). May be a non-SA supplier."
                    ),
                ))

        # Validate VAT consistency: vat ≈ subtotal × 0.15 (SA VAT rate)
        subtotal_data = fields.get("subtotal", {})
        vat_amount_data = fields.get("vat_amount", {})
        subtotal_value = subtotal_data.get("value")
        vat_amount_value = vat_amount_data.get("value")

        if subtotal_value and vat_amount_value:
            try:
                subtotal = Decimal(str(subtotal_value))
                vat_amt = Decimal(str(vat_amount_value))
                expected_vat = subtotal * Decimal("0.15")
                discrepancy = abs(vat_amt - expected_vat)
                if subtotal > 0 and (discrepancy / subtotal) > Decimal("0.05"):
                    report.add(FieldValidationResult(
                        field_name="vat_amount",
                        status="warning",
                        message=(
                            f"VAT amount ({vat_amt}) differs from expected 15% "
                            f"({expected_vat:.2f}) by more than 5%. "
                            "May be a different rate or non-SA invoice."
                        ),
                    ))
            except (InvalidOperation, ZeroDivisionError):
                pass

        # Cross-check: subtotal + VAT ≈ total
        total_for_sum = fields.get("total_amount", {}).get("value")
        if subtotal_value and vat_amount_value and total_for_sum:
            try:
                subtotal = Decimal(str(subtotal_value))
                vat_amt = Decimal(str(vat_amount_value))
                total = Decimal(str(total_for_sum))
                expected_total = subtotal + vat_amt
                if abs(expected_total - total) > Decimal("0.05"):
                    report.add(FieldValidationResult(
                        field_name="total_amount",
                        status="warning",
                        message=(
                            f"Total ({total}) does not match subtotal ({subtotal}) "
                            f"+ VAT ({vat_amt}) = {expected_total}."
                        ),
                    ))
                    report.should_route_to_review = True
            except InvalidOperation:
                pass

        # Email must look like an email
        email_value = (fields.get("supplier_email", {}) or {}).get("value")
        if email_value and "@" not in str(email_value):
            report.add(FieldValidationResult(
                field_name="supplier_email",
                status="warning",
                message="Supplier email does not look like an email address.",
            ))

        # Route to review if any required field has low confidence
        low_confidence_required = [
            f for f in self.REQUIRED_FIELDS
            if (fields.get(f, {}).get("confidence") or 0.0) < confidence_threshold
            and fields.get(f, {}).get("value")
        ]
        if low_confidence_required:
            report.should_route_to_review = True

        return report

    @staticmethod
    def _parse_date(value: str) -> date | None:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(str(value), fmt).date()
            except ValueError:
                continue
        return None
