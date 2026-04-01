# src/listingjet/services/storage.py
"""
S3-backed storage service.

All asset uploads use a consistent key scheme:
  listings/{listing_id}/{asset_type}/{filename}

Presigned URLs expire in 1 hour by default.
"""
import io
import logging

import boto3
from botocore.exceptions import ClientError

from listingjet.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when an S3 operation fails."""


class StorageService:
    def __init__(self, bucket: str = None, region: str = None):
        self._bucket = bucket or settings.s3_bucket_name
        self._region = region or settings.aws_region
        self._client = boto3.client("s3", region_name=self._region)

    def upload(self, key: str, data: bytes | io.IOBase, content_type: str) -> str:
        """Upload bytes or file-like object. Returns the S3 key."""
        try:
            if isinstance(data, (bytes, bytearray)):
                data = io.BytesIO(data)
            self._client.upload_fileobj(
                data,
                self._bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            return key
        except ClientError as e:
            logger.exception("S3 upload failed key=%s", key)
            raise StorageError(f"Failed to upload {key}: {e}") from e

    # Convenience alias used by VideoAgent
    def upload_bytes(self, data: bytes, key: str, content_type: str) -> str:
        return self.upload(key=key, data=data, content_type=content_type)

    # Allowed content types for photo uploads
    ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

    def presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 300,
        max_size: int | None = None,
    ) -> str:
        """Generate a presigned PUT URL with content-type and size enforcement."""
        if content_type not in self.ALLOWED_UPLOAD_TYPES:
            raise ValueError(f"Content type '{content_type}' not allowed. Must be one of: {self.ALLOWED_UPLOAD_TYPES}")
        try:
            conditions = [
                ["content-length-range", 1, max_size or self.MAX_UPLOAD_SIZE],
                ["eq", "$Content-Type", content_type],
            ]
            fields = {"Content-Type": content_type}
            return self._client.generate_presigned_post(
                Bucket=self._bucket,
                Key=key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.exception("S3 presigned upload URL failed key=%s", key)
            raise StorageError(f"Failed to generate upload URL for {key}: {e}") from e

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned GET URL."""
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.exception("S3 presigned GET URL failed key=%s", key)
            raise StorageError(f"Failed to generate download URL for {key}: {e}") from e

    def download(self, key: str) -> bytes:
        """Download an object from S3 and return its bytes."""
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            logger.exception("S3 download failed key=%s", key)
            raise StorageError(f"Failed to download {key}: {e}") from e

    def delete(self, key: str) -> None:
        """Delete an object from S3."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError as e:
            logger.exception("S3 delete failed key=%s", key)
            raise StorageError(f"Failed to delete {key}: {e}") from e


# Module-level singleton — reuses the same boto3 S3 client across requests
_default_storage: StorageService | None = None


def get_storage() -> StorageService:
    global _default_storage
    if _default_storage is None:
        _default_storage = StorageService()
    return _default_storage
