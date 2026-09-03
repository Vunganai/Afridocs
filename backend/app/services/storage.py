"""
Document storage service.
In development: stores files on local disk under backend/uploads/.
In production: stores to Azure Blob Storage.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

import aiofiles
import structlog
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", "/app/uploads"))


class StorageService:
    """
    Abstracts file storage — local filesystem for dev, Azure Blob for prod.
    All methods are async.
    """

    def __init__(self):
        self._settings = get_settings()

    async def save(self, file_bytes: bytes, original_filename: str) -> tuple[str, str]:
        """
        Save a file and return (storage_path, sha256_hash).
        """
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        ext = Path(original_filename).suffix.lower()
        blob_name = f"{uuid.uuid4().hex}{ext}"

        if self._settings.is_production:
            storage_path = await self._save_to_azure(file_bytes, blob_name)
        else:
            storage_path = await self._save_to_local(file_bytes, blob_name)

        return storage_path, file_hash

    async def read(self, storage_path: str) -> bytes:
        """Read a file back from storage. Returns raw bytes."""
        if self._settings.is_production:
            return await self._read_from_azure(storage_path)
        return await self._read_from_local(storage_path)

    async def delete(self, storage_path: str) -> None:
        """Delete a file from storage."""
        if self._settings.is_production:
            await self._delete_from_azure(storage_path)
        else:
            await self._delete_from_local(storage_path)

    # ── Local ──────────────────────────────────────────────────────────────

    async def _save_to_local(self, file_bytes: bytes, blob_name: str) -> str:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = UPLOADS_DIR / blob_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_bytes)
        storage_path = f"local://{blob_name}"
        logger.debug("file_saved_local", path=str(file_path))
        return storage_path

    async def _read_from_local(self, storage_path: str) -> bytes:
        blob_name = storage_path.replace("local://", "")
        file_path = UPLOADS_DIR / blob_name
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    async def _delete_from_local(self, storage_path: str) -> None:
        blob_name = storage_path.replace("local://", "")
        file_path = UPLOADS_DIR / blob_name
        if file_path.exists():
            file_path.unlink()

    # ── Azure Blob ─────────────────────────────────────────────────────────

    def _get_blob_client(self):
        s = self._settings
        account_url = f"https://{s.azure_storage_account_name}.blob.core.windows.net"
        return BlobServiceClient(
            account_url=account_url,
            credential=s.azure_storage_account_key,
        )

    async def _save_to_azure(self, file_bytes: bytes, blob_name: str) -> str:
        try:
            client = self._get_blob_client()
            blob_client = client.get_blob_client(
                container=self._settings.azure_storage_container_name,
                blob=blob_name,
            )
            blob_client.upload_blob(file_bytes, overwrite=False)
            storage_path = (
                f"azure://{self._settings.azure_storage_container_name}/{blob_name}"
            )
            logger.info("file_saved_azure", blob=blob_name)
            return storage_path
        except AzureError as exc:
            logger.error("azure_storage_upload_error", error=str(exc))
            raise

    async def _read_from_azure(self, storage_path: str) -> bytes:
        blob_name = storage_path.split("/")[-1]
        client = self._get_blob_client()
        blob_client = client.get_blob_client(
            container=self._settings.azure_storage_container_name,
            blob=blob_name,
        )
        download = blob_client.download_blob()
        return download.readall()

    async def _delete_from_azure(self, storage_path: str) -> None:
        blob_name = storage_path.split("/")[-1]
        client = self._get_blob_client()
        blob_client = client.get_blob_client(
            container=self._settings.azure_storage_container_name,
            blob=blob_name,
        )
        blob_client.delete_blob()
