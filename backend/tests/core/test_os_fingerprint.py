from unittest.mock import AsyncMock, patch

import pytest

from app.core.os_fingerprint import OSFingerprinter


class TestOSFingerprinter:
    async def test_basic_detection_windows_hint(self):
        fp = OSFingerprinter()
        fp.nmap_available = False
        result = await fp.detect_os("127.0.0.1", open_ports=[445, 3389])
        assert result["os_name"] == "Windows"
        assert result["os_accuracy"] == 60
        assert result["os_details"]["method"] == "heuristic"

    async def test_basic_detection_linux_hint(self):
        fp = OSFingerprinter()
        fp.nmap_available = False
        result = await fp.detect_os("127.0.0.1", open_ports=[22])
        assert result["os_name"] == "Linux"
        assert result["os_accuracy"] == 40

    async def test_basic_detection_unknown_when_no_ports(self):
        fp = OSFingerprinter()
        fp.nmap_available = False
        result = await fp.detect_os("127.0.0.1", open_ports=None)
        assert result["os_name"] == "Unknown"
        assert result["os_accuracy"] == 0

    async def test_nmap_path_uses_best_match(self):
        fp = OSFingerprinter()
        fp.nmap_available = True

        class FakeNM:
            def all_hosts(self):
                return ["127.0.0.1"]

            def __getitem__(self, host):
                return {
                    "osmatch": [
                        {"name": "Linux 5.x", "accuracy": "95"},
                        {"name": "Linux 4.x", "accuracy": "80"},
                    ]
                }

            def scan(self, *a, **k):
                return None

        fake_nmap_module = type("M", (), {"PortScanner": FakeNM})

        with patch.dict("sys.modules", {"nmap": fake_nmap_module}):
            result = await fp._nmap_os_detection("127.0.0.1")

        assert result["os_name"] == "Linux 5.x"
        assert result["os_accuracy"] == 95
        assert len(result["os_details"]["matches"]) == 2
