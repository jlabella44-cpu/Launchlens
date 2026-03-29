import uuid

import pytest
from sqlalchemy import select

from listingjet.models.api_key import APIKey
from listingjet.services.api_keys import create_api_key, generate_key, hash_key, validate_api_key


def test_generate_key_format():
    key = generate_key()
    assert key.startswith("ll_")
    assert len(key) == 3 + 32  # prefix + 32 hex chars


def test_hash_key_deterministic():
    key = "ll_abc123"
    assert hash_key(key) == hash_key(key)
    assert hash_key(key) != hash_key("ll_other")


@pytest.mark.asyncio
async def test_create_api_key(db_session):
    tenant_id = uuid.uuid4()
    api_key, plaintext = await create_api_key(db_session, tenant_id, "test-key")
    assert plaintext.startswith("ll_")
    assert api_key.name == "test-key"
    assert api_key.key_hash == hash_key(plaintext)
    assert api_key.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_validate_api_key_success(db_session):
    tenant_id = uuid.uuid4()
    _, plaintext = await create_api_key(db_session, tenant_id, "validate-me")
    found = await validate_api_key(db_session, plaintext)
    assert found is not None
    assert found.last_used_at is not None


@pytest.mark.asyncio
async def test_validate_api_key_invalid(db_session):
    result = await validate_api_key(db_session, "ll_does_not_exist_at_all_1234")
    assert result is None
