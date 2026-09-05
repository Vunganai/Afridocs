"""
Live processing progress for uploaded invoices.
Stored in Redis so the UI can poll without waiting for the full pipeline commit.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

PROGRESS_TTL_SECONDS = 60 * 60
PIPELINE_STEPS: list[dict[str, str]] = [
    {"id": "queued", "label": "Upload received"},
    {"id": "reading", "label": "Loading file from storage"},
    {"id": "ocr", "label": "Reading invoice (OCR)"},
    {"id": "classify", "label": "Classifying document"},
    {"id": "extract", "label": "Extracting invoice fields"},
    {"id": "refine", "label": "Improving extraction accuracy"},
    {"id": "validate", "label": "Validating amounts and rules"},
    {"id": "save", "label": "Saving results"},
]

_STAGE_INDEX = {step["id"]: i for i, step in enumerate(PIPELINE_STEPS)}
_TERMINAL_STATUSES = {
    "extracted",
    "review_required",
    "approved",
    "rejected",
    "duplicate",
    "failed",
}

_redis = None


def _client():
    global _redis
    if _redis is None:
        import redis

        _redis = redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


def _key(document_id: str) -> str:
    return f"afridocs:progress:{document_id}"


def set_progress(
    document_id: str,
    *,
    stage: str,
    percent: int,
    message: str,
    status: str = "processing",
    error: str | None = None,
) -> None:
    payload = {
        "stage": stage,
        "percent": max(0, min(100, percent)),
        "message": message,
        "status": status,
        "error": error,
        "done": status in _TERMINAL_STATUSES or stage == "complete",
    }
    try:
        _client().setex(_key(document_id), PROGRESS_TTL_SECONDS, json.dumps(payload))
    except Exception as exc:
        logger.warning("progress_write_failed", document_id=document_id, error=str(exc))


def get_progress(document_id: str) -> dict[str, Any] | None:
    try:
        raw = _client().get(_key(document_id))
    except Exception as exc:
        logger.warning("progress_read_failed", document_id=document_id, error=str(exc))
        return None
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def build_steps(stage: str, *, done: bool, failed: bool) -> list[dict[str, str]]:
    current = _STAGE_INDEX.get(stage, 0)
    if done and not failed:
        current = len(PIPELINE_STEPS)
    steps = []
    for i, step in enumerate(PIPELINE_STEPS):
        if failed and i == current:
            state = "error"
        elif i < current or (done and not failed):
            state = "done"
        elif i == current:
            state = "active"
        else:
            state = "pending"
        steps.append({**step, "state": state})
    return steps


def fallback_from_status(status: str, processing_error: str | None = None) -> dict[str, Any]:
    """When Redis has no payload yet, infer a coarse stage from document.status."""
    if status == "pending":
        return {
            "stage": "queued",
            "percent": 8,
            "message": "Waiting for the processing worker to pick up this invoice.",
            "status": status,
            "error": None,
            "done": False,
        }
    if status == "processing":
        return {
            "stage": "ocr",
            "percent": 35,
            "message": "Invoice is being processed.",
            "status": status,
            "error": None,
            "done": False,
        }
    if status == "failed":
        return {
            "stage": "save",
            "percent": 100,
            "message": processing_error or "Processing failed.",
            "status": status,
            "error": processing_error,
            "done": True,
        }
    return {
        "stage": "complete",
        "percent": 100,
        "message": "Processing complete.",
        "status": status,
        "error": None,
        "done": True,
    }
