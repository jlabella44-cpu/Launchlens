"""ClamAV virus scanner service for uploaded assets."""

import logging

import clamd

from listingjet.config import settings

logger = logging.getLogger(__name__)


class ClamAVScanner:
    """Scans file bytes for malware via ClamAV daemon."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        self.host = host or settings.clamav_host
        self.port = port or settings.clamav_port
        self._client: clamd.ClamdNetworkSocket | None = None

    def _get_client(self) -> clamd.ClamdNetworkSocket:
        if self._client is None:
            self._client = clamd.ClamdNetworkSocket(
                host=self.host,
                port=self.port,
                timeout=30,
            )
        return self._client

    def scan_bytes(self, data: bytes) -> tuple[bool, str]:
        """Scan raw bytes. Returns (is_clean, detail)."""
        try:
            client = self._get_client()
            result = client.instream(data)
            status, detail = result.get("stream", ("ERROR", "No result"))
            is_clean = status == "OK"
            if not is_clean:
                logger.warning("clamav_threat_detected", extra={"detail": detail})
            return is_clean, detail
        except Exception as e:
            logger.error("clamav_scan_failed", extra={"error": str(e)})
            raise

    def ping(self) -> bool:
        """Check if ClamAV daemon is reachable."""
        try:
            return self._get_client().ping() == "PONG"
        except Exception:
            return False
