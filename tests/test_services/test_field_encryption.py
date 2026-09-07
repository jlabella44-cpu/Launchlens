from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from listingjet.services import field_encryption as fe


def test_roundtrip_with_key():
    key = Fernet.generate_key().decode()
    with patch.object(fe.settings, "field_encryption_key", key):
        assert fe.decrypt(fe.encrypt("secret")) == "secret"


def test_no_key_in_development_passes_through():
    with patch.object(fe.settings, "field_encryption_key", ""), \
         patch.object(fe.settings, "app_env", "development"):
        assert fe.encrypt("x") == "x"
        assert fe.decrypt("x") == "x"


def test_no_key_in_production_raises():
    with patch.object(fe.settings, "field_encryption_key", ""), \
         patch.object(fe.settings, "app_env", "production"):
        with pytest.raises(RuntimeError, match="FIELD_ENCRYPTION_KEY"):
            fe.encrypt("x")
        with pytest.raises(RuntimeError, match="FIELD_ENCRYPTION_KEY"):
            fe.decrypt("x")
