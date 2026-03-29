"""Tests for the ClamAV virus scanner service."""
import sys
from unittest.mock import MagicMock, patch

import pytest

# clamd is not installed in test env — stub it before importing the scanner module.
_mock_clamd_module = MagicMock()
sys.modules.setdefault("clamd", _mock_clamd_module)


@pytest.fixture(autouse=True)
def _reset_scanner():
    """Re-mock clamd internals for each test."""
    _mock_clamd_module.reset_mock()
    yield


@pytest.fixture
def _mock_settings():
    """Provide dummy ClamAV settings."""
    with patch("listingjet.services.scanner.settings") as s:
        s.clamav_host = "localhost"
        s.clamav_port = 3310
        yield s


def test_scan_bytes_clean(_mock_settings):
    """Clean files should return (True, 'OK')."""
    from listingjet.services.scanner import ClamAVScanner

    mock_socket = MagicMock()
    mock_socket.instream.return_value = {"stream": ("OK", "No threat")}
    _mock_clamd_module.ClamdNetworkSocket.return_value = mock_socket

    scanner = ClamAVScanner(host="localhost", port=3310)
    is_clean, detail = scanner.scan_bytes(b"safe content")

    assert is_clean is True
    assert detail == "No threat"
    mock_socket.instream.assert_called_once_with(b"safe content")


def test_scan_bytes_threat_detected(_mock_settings):
    """Infected files should return (False, <threat name>)."""
    from listingjet.services.scanner import ClamAVScanner

    mock_socket = MagicMock()
    mock_socket.instream.return_value = {"stream": ("FOUND", "Eicar-Test-Signature")}
    _mock_clamd_module.ClamdNetworkSocket.return_value = mock_socket

    scanner = ClamAVScanner(host="localhost", port=3310)
    is_clean, detail = scanner.scan_bytes(b"X5O!P%@AP...")

    assert is_clean is False
    assert "Eicar" in detail


def test_scan_bytes_raises_on_connection_error(_mock_settings):
    """If ClamAV daemon is unreachable, scan_bytes should propagate the exception."""
    from listingjet.services.scanner import ClamAVScanner

    mock_socket = MagicMock()
    mock_socket.instream.side_effect = ConnectionError("daemon unreachable")
    _mock_clamd_module.ClamdNetworkSocket.return_value = mock_socket

    scanner = ClamAVScanner(host="localhost", port=3310)
    with pytest.raises(ConnectionError):
        scanner.scan_bytes(b"data")


def test_ping_success(_mock_settings):
    """ping() should return True when ClamAV replies PONG."""
    from listingjet.services.scanner import ClamAVScanner

    mock_socket = MagicMock()
    mock_socket.ping.return_value = "PONG"
    _mock_clamd_module.ClamdNetworkSocket.return_value = mock_socket

    scanner = ClamAVScanner(host="localhost", port=3310)
    assert scanner.ping() is True


def test_ping_failure(_mock_settings):
    """ping() should return False when ClamAV is unreachable."""
    from listingjet.services.scanner import ClamAVScanner

    mock_socket = MagicMock()
    mock_socket.ping.side_effect = ConnectionError("down")
    _mock_clamd_module.ClamdNetworkSocket.return_value = mock_socket

    scanner = ClamAVScanner(host="localhost", port=3310)
    assert scanner.ping() is False
