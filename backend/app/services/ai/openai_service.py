"""
Azure OpenAI service client.
Handles document classification and extraction gap-filling.
"""

from __future__ import annotations

import json

import structlog
from openai import AzureOpenAI, APIError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)

CLASSIFICATION_SYSTEM_PROMPT = """
You are a document classification expert for an African business document processing system.
Your task is to classify a document based on its extracted text content.

Respond ONLY with a valid JSON object in this exact format:
{
  "document_type": "<type>",
  "confidence": <0.0 to 1.0>,
  "reasoning": "<one sentence>"
}

Valid document types: invoice, purchase_order, delivery_note, contract, bank_statement,
identity_document, receipt, other

If the document appears to be an invoice, set confidence >= 0.8.
If you cannot determine the type, use "other" with low confidence.
""".strip()

EXTRACTION_GAP_FILL_SYSTEM_PROMPT = """
You are an expert at extracting structured data from business invoices for African companies.
You will receive:
1. The raw text extracted from an invoice via OCR
2. Fields that were NOT successfully extracted by the primary OCR system (missing or low confidence)

Your task is to attempt to extract ONLY the missing fields from the raw text.

Rules:
- Only return fields you are confident about (confidence >= 0.7)
- For currency, default to ZAR if you see South African context but no explicit currency
- For dates, use ISO 8601 format (YYYY-MM-DD)
- For amounts, return only the numeric value as a string (e.g. "1250.00")
- For VAT numbers, South African format is 10 digits (no prefix)

Respond ONLY with a valid JSON object mapping field_name → {value, confidence}.
Example: {"invoice_number": {"value": "INV-2024-001", "confidence": 0.95}}
""".strip()


def get_openai_client():
    settings = get_settings()
    # Azure AI Foundry endpoint requires AzureOpenAI client with the base resource URL
    # The /api/projects/... path is appended automatically by the SDK
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )


class OpenAIService:
    """
    Wraps Azure OpenAI for document classification and extraction gap-filling.
    All responses are structured JSON — no free-form text generation.
    """

    def __init__(self):
        self._client = get_openai_client()
        self._settings = get_settings()
        self._deployment = self._settings.azure_openai_deployment_name

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def classify_document(self, extracted_text: str) -> dict:
        """
        Classify a document using GPT-4o.
        Returns: {document_type, confidence, reasoning}
        """
        logger.info("openai_classify_start")
        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Classify this document:\n\n{extracted_text[:4000]}",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=200,
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            logger.info(
                "openai_classify_complete",
                document_type=result.get("document_type"),
                confidence=result.get("confidence"),
            )
            return result
        except (APIError, json.JSONDecodeError) as exc:
            logger.error("openai_classify_error", error=str(exc))
            raise ExternalServiceError(f"OpenAI classification failed: {exc}") from exc

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    def fill_extraction_gaps(
        self,
        raw_text: str,
        missing_fields: list[str],
    ) -> dict[str, dict]:
        """
        Use GPT-4o to attempt extraction of fields that the primary OCR missed.
        Returns: {field_name: {value, confidence}}
        """
        if not missing_fields:
            return {}

        logger.info("openai_gap_fill_start", missing_fields=missing_fields)
        try:
            prompt = (
                f"Missing fields to extract: {', '.join(missing_fields)}\n\n"
                f"Raw invoice text:\n{raw_text[:6000]}"
            )
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": EXTRACTION_GAP_FILL_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=500,
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            logger.info("openai_gap_fill_complete", filled_fields=list(result.keys()))
            return result
        except (APIError, json.JSONDecodeError) as exc:
            logger.error("openai_gap_fill_error", error=str(exc))
            # Gap-filling is best-effort — don't fail the pipeline
            return {}
