from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

from listingjet.services.storage import StorageService


@pytest.fixture
def s3_service():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
        yield StorageService(bucket="test-bucket", region="us-east-1")


def test_upload_bytes_returns_key(s3_service):
    key = s3_service.upload(key="listings/abc/hero.jpg", data=b"fake-image-bytes", content_type="image/jpeg")
    assert key == "listings/abc/hero.jpg"


def test_presigned_url_returns_string(s3_service):
    s3_service.upload(key="listings/abc/hero.jpg", data=b"x", content_type="image/jpeg")
    url = s3_service.presigned_url(key="listings/abc/hero.jpg", expires_in=3600)
    assert url.startswith("http")  # moto returns http://, real S3 returns https://


def test_delete_removes_object(s3_service):
    client = boto3.client("s3", region_name="us-east-1")
    s3_service.upload(key="listings/abc/hero.jpg", data=b"x", content_type="image/jpeg")
    s3_service.delete(key="listings/abc/hero.jpg")
    objs = client.list_objects_v2(Bucket="test-bucket").get("Contents", [])
    assert len(objs) == 0


def test_upload_file_like_object(s3_service):
    import io
    buf = io.BytesIO(b"image-data")
    key = s3_service.upload(key="listings/abc/photo.jpg", data=buf, content_type="image/jpeg")
    assert key == "listings/abc/photo.jpg"


def test_default_aws_client_no_endpoint_url():
    """Without s3_endpoint_url set, boto3 hits AWS (no custom endpoint)."""
    with patch("listingjet.services.storage.boto3.client") as mock_client:
        with patch("listingjet.services.storage.settings") as mock_settings:
            mock_settings.s3_bucket_name = "default-bucket"
            mock_settings.aws_region = "us-east-1"
            mock_settings.s3_endpoint_url = ""
            mock_settings.s3_access_key_id = ""
            mock_settings.s3_secret_access_key = ""
            StorageService()
            kwargs = mock_client.call_args[1]
            assert kwargs == {"region_name": "us-east-1"}


def test_r2_endpoint_and_creds_passed_to_boto3():
    """When s3_endpoint_url + creds are set (R2 case), they reach boto3."""
    with patch("listingjet.services.storage.boto3.client") as mock_client:
        with patch("listingjet.services.storage.settings") as mock_settings:
            mock_settings.s3_bucket_name = "media"
            mock_settings.aws_region = "auto"
            mock_settings.s3_endpoint_url = "https://acct.r2.cloudflarestorage.com"
            mock_settings.s3_access_key_id = "AKIA-r2"
            mock_settings.s3_secret_access_key = "secret-r2"
            StorageService()
            kwargs = mock_client.call_args[1]
            assert kwargs["endpoint_url"] == "https://acct.r2.cloudflarestorage.com"
            assert kwargs["aws_access_key_id"] == "AKIA-r2"
            assert kwargs["aws_secret_access_key"] == "secret-r2"
            assert kwargs["region_name"] == "auto"
