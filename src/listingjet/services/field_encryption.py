"""Fernet-based field encryption for sensitive values stored in the database (e.g. IDX API keys)."""

from cryptography.fernet import Fernet, InvalidToken

from listingjet.config import settings


def _get_fernet() -> Fernet | None:
    key = settings.field_encryption_key
    if not key:
        return None
    return Fernet(key.encode())


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns ciphertext. Falls back to plaintext if no key configured."""
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a ciphertext string. Falls back to returning as-is if no key or decryption fails (plaintext migration)."""
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        # Graceful migration: value was stored before encryption was enabled
        return ciphertext
