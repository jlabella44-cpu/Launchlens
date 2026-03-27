# tests/test_api/test_auth.py
import pytest
from launchlens.models.user import User, UserRole


def test_user_model_has_password_hash():
    """User model must have a password_hash field."""
    import inspect
    annotations = {}
    for cls in reversed(User.__mro__):
        if hasattr(cls, '__annotations__'):
            annotations.update(cls.__annotations__)
    assert "password_hash" in annotations, "User model missing password_hash field"
