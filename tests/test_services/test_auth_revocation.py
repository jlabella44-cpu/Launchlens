from unittest.mock import MagicMock, patch

import pytest
import redis
from fastapi import HTTPException

from listingjet.services import auth as auth_svc

# Captured at import time, before the autouse `_mock_external_services` fixture
# in conftest.py patches `auth_svc.get_redis` for every test. test_get_redis_is_cached
# needs the *real* implementation to verify caching, so it restores this reference
# for the duration of that test.
_real_get_redis = auth_svc.get_redis


def test_is_token_revoked_true_when_key_exists():
    r = MagicMock()
    r.exists.return_value = 1
    with patch.object(auth_svc, "get_redis", return_value=r):
        assert auth_svc.is_token_revoked("tok") is True
    r.exists.assert_called_once_with("token_revoked:tok")


def test_is_token_revoked_fails_closed_when_redis_errors():
    r = MagicMock()
    r.exists.side_effect = redis.exceptions.ConnectionError("down")
    with patch.object(auth_svc, "get_redis", return_value=r):
        with pytest.raises(HTTPException) as exc:
            auth_svc.is_token_revoked("tok")
    assert exc.value.status_code == 503


def test_is_token_revoked_propagates_unexpected_errors():
    r = MagicMock()
    r.exists.side_effect = TypeError("boom")
    with patch.object(auth_svc, "get_redis", return_value=r):
        with pytest.raises(TypeError):
            auth_svc.is_token_revoked("tok")


def test_get_redis_is_cached():
    auth_svc._redis_client = None
    with patch.object(auth_svc, "get_redis", _real_get_redis):
        with patch("redis.from_url") as from_url:
            from_url.return_value = MagicMock()
            a = auth_svc.get_redis()
            b = auth_svc.get_redis()
    assert a is b
    assert from_url.call_count == 1
    auth_svc._redis_client = None
