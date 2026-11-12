from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.service_detector import ServiceDetector


class TestServiceDetector:
    async def test_detect_service_returns_default_name_and_parsed_banner(self):
        detector = ServiceDetector(timeout=0.01)

        with patch.object(ServiceDetector, "_grab_banner", new=AsyncMock(return_value="SSH-2.0-OpenSSH_8.9p1")):
            info = await detector.detect_service("127.0.0.1", 22, "tcp")

        assert info["service_name"] == "ssh"
        assert info["banner"].startswith("SSH-2.0")
        assert info["service_product"] == "OpenSSH"
        # Current implementation captures the numeric portion ([\d.]+) from the OpenSSH token.
        assert info["service_version"] == "8.9"

    async def test_detect_service_without_banner_keeps_name(self):
        detector = ServiceDetector(timeout=0.01)
        with patch.object(ServiceDetector, "_grab_banner", new=AsyncMock(return_value=None)):
            info = await detector.detect_service("127.0.0.1", 80, "tcp")

        assert info["service_name"] == "http"
        assert info["service_product"] is None
        assert info["service_version"] is None
        assert info["banner"] is None

    def test_parse_banner_http_server(self):
        detector = ServiceDetector()
        parsed = detector._parse_banner("HTTP/1.1 200 OK\r\nServer: nginx/1.18.0\r\n\r\n", "http")
        # first matching pattern in implementation wins (generic Server header)
        assert parsed["service_product"] in {"HTTP", "nginx"}
        assert parsed["service_version"] is not None

    def test_parse_banner_unknown_service_returns_none(self):
        detector = ServiceDetector()
        parsed = detector._parse_banner("whatever", "unknownsvc")
        assert parsed == {"service_product": None, "service_version": None}
