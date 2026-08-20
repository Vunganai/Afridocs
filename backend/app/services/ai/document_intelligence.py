"""
Azure AI Document Intelligence client.
Handles OCR and pre-built invoice model extraction.
"""

from __future__ import annotations

import structlog
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)


def get_document_intelligence_client() -> DocumentIntelligenceClient:
    settings = get_settings()
    return DocumentIntelligenceClient(
        endpoint=settings.azure_document_intelligence_endpoint,
        credential=AzureKeyCredential(settings.azure_document_intelligence_key),
    )


class InvoiceExtractionResult:
    """Normalised extraction result from Azure Document Intelligence."""

    def __init__(self, raw: AnalyzeResult):
        self._raw = raw
        self.fields: dict[str, dict] = {}
        self._parse()

    def _parse(self) -> None:
        """
        Parse the Azure prebuilt-invoice model output into a flat dict
        with field_name → {value, confidence} entries.
        """
        if not self._raw.documents:
            return

        doc = self._raw.documents[0]
        field_map = {
            "invoice_number": "InvoiceId",
            "invoice_date": "InvoiceDate",
            "due_date": "DueDate",
            "supplier_name": "VendorName",
            "supplier_vat_number": "VendorTaxId",
            "supplier_email": "VendorAddress",  # Best-effort from address block
            "total_amount": "InvoiceTotal",
            "vat_amount": "TotalTax",
            "subtotal": "SubTotal",
            "currency": "CurrencyCode",
            "purchase_order_ref": "PurchaseOrder",
            "payment_terms": "PaymentTerm",
        }

        for our_name, azure_name in field_map.items():
            azure_field = (doc.fields or {}).get(azure_name)
            if azure_field is None:
                self.fields[our_name] = {"value": None, "confidence": 0.0}
                continue

            # Extract typed value
            value = None
            if hasattr(azure_field, "value_string") and azure_field.value_string:
                value = azure_field.value_string
            elif hasattr(azure_field, "value_date") and azure_field.value_date:
                value = str(azure_field.value_date)
            elif hasattr(azure_field, "value_currency") and azure_field.value_currency:
                value = str(azure_field.value_currency.amount)
            elif hasattr(azure_field, "content") and azure_field.content:
                value = azure_field.content

            self.fields[our_name] = {
                "value": value,
                "confidence": azure_field.confidence or 0.0,
            }

        # Parse line items
        line_items_field = (doc.fields or {}).get("Items")
        if line_items_field and hasattr(line_items_field, "value_array"):
            self.fields["line_items"] = {
                "value": self._parse_line_items(line_items_field.value_array),
                "confidence": line_items_field.confidence or 0.0,
            }

    def _parse_line_items(self, items) -> list[dict]:
        result = []
        for item in (items or []):
            if not hasattr(item, "value_object"):
                continue
            obj = item.value_object or {}
            result.append({
                "description": self._get_field_value(obj, "Description"),
                "quantity": self._get_field_value(obj, "Quantity"),
                "unit_price": self._get_field_value(obj, "UnitPrice"),
                "amount": self._get_field_value(obj, "Amount"),
            })
        return result

    def _get_field_value(self, obj: dict, key: str) -> str | None:
        field = obj.get(key)
        if not field:
            return None
        if hasattr(field, "value_string"):
            return field.value_string
        if hasattr(field, "content"):
            return field.content
        return None

    @property
    def min_confidence(self) -> float:
        """Lowest confidence score across all extracted fields."""
        scores = [f["confidence"] for f in self.fields.values() if f["confidence"] is not None]
        return min(scores) if scores else 0.0

    @property
    def avg_confidence(self) -> float:
        scores = [f["confidence"] for f in self.fields.values() if f["confidence"] is not None]
        return sum(scores) / len(scores) if scores else 0.0

    def to_dict(self) -> dict:
        return self.fields


class DocumentIntelligenceService:
    """
    Wraps Azure AI Document Intelligence with retry logic and
    normalises the output for use in the processing pipeline.
    """

    def __init__(self):
        self._client = get_document_intelligence_client()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def analyze_invoice(self, file_bytes: bytes, content_type: str) -> InvoiceExtractionResult:
        """
        Submit a document to the Azure prebuilt-invoice model.
        Returns a normalised InvoiceExtractionResult.
        """
        logger.info("azure_doc_intel_analyze_start", content_type=content_type)
        try:
            poller = self._client.begin_analyze_document(
                model_id="prebuilt-invoice",
                body=file_bytes,
                content_type=content_type,
            )
            result: AnalyzeResult = poller.result()
            logger.info(
                "azure_doc_intel_analyze_complete",
                num_documents=len(result.documents or []),
            )
            return InvoiceExtractionResult(result)
        except HttpResponseError as exc:
            logger.error("azure_doc_intel_error", status_code=exc.status_code, detail=str(exc))
            raise ExternalServiceError(
                f"Azure Document Intelligence failed: {exc.message}"
            ) from exc
