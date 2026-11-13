import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.core.scanner import NetworkScanner, DEFAULT_UDP_PORTS
from app.models.scan import ScanType, PortState


@pytest.fixture
def scanner():
    s = NetworkScanner()
    # Never perform real network/service/OS probing or reverse DNS in tests.
    s.resolve_hostnames = False
    s.network_mapper = Mock()
    s.network_mapper.discover_hosts = AsyncMock()
    s.port_scanner = AsyncMock()
    s.service_detector = AsyncMock()
    s.os_fingerprinter = AsyncMock()

    s.network_mapper.parse_target.return_value = ["192.168.1.10"]
    s.network_mapper.discover_hosts.return_value = ["192.168.1.10"]
    s.service_detector.detect_service.return_value = {
        "service_name": "mocksvc",
        "service_product": "mock",
        "service_version": "1.0",
        "banner": None,
    }
    s.os_fingerprinter.detect_os.return_value = {
        "os_name": None,
        "os_accuracy": None,
        "os_details": None,
    }
    return s


class TestNetworkScannerComprehensive:
    async def test_comprehensive_uses_default_udp_ports_and_preserves_protocols(self, scanner):
        # TCP SYN returns one open port, UDP returns one open port (different number)
        scanner.port_scanner.tcp_syn_scan.return_value = {80: PortState.OPEN, 22: PortState.CLOSED}
        scanner.port_scanner.udp_scan.return_value = {53: PortState.OPEN, 123: PortState.CLOSED}

        result = await NetworkScanner.scan(
            scanner,
            target="192.168.1.10",
            scan_type=ScanType.COMPREHENSIVE,
            port_range="22,80",
            service_detection=True,
            os_detection=False,
        )

        # P0 regression: must not raise NameError and must use default UDP baseline
        scanner.port_scanner.udp_scan.assert_awaited_once()
        udp_args = scanner.port_scanner.udp_scan.await_args.args
        assert udp_args[0] == "192.168.1.10"
        assert udp_args[1] == DEFAULT_UDP_PORTS

        assert result["hosts_up"] == 1
        assert result["total_ports_found"] == 2

        host = result["results"][0]
        ports = {(p["port_number"], p["protocol"]): p for p in host["ports"]}

        assert (80, "tcp") in ports
        assert (53, "udp") in ports
        assert ports[(80, "tcp")]["state"] == PortState.OPEN.value
        assert ports[(53, "udp")]["state"] == PortState.OPEN.value

        # Service detection called with correct protocol per port
        calls = {(c.args[1], c.args[2]) for c in scanner.service_detector.detect_service.await_args_list}
        assert (80, "tcp") in calls
        assert (53, "udp") in calls

    async def test_comprehensive_same_port_number_different_protocols_are_distinct(self, scanner):
        # Same port number open on both transports should produce two entries with correct protocols
        scanner.port_scanner.tcp_syn_scan.return_value = {53: PortState.OPEN}
        scanner.port_scanner.udp_scan.return_value = {53: PortState.OPEN}

        result = await NetworkScanner.scan(
            scanner,
            target="192.168.1.10",
            scan_type=ScanType.COMPREHENSIVE,
            service_detection=False,
        )

        host = result["results"][0]
        protos = sorted([p["protocol"] for p in host["ports"] if p["port_number"] == 53])
        assert protos == ["tcp", "udp"]
        assert result["total_ports_found"] == 2


class TestNetworkScannerProtocols:
    async def test_tcp_connect_labels_protocol_tcp(self, scanner):
        scanner.port_scanner.tcp_connect_scan.return_value = {443: PortState.OPEN}

        result = await NetworkScanner.scan(
            scanner,
            target="192.168.1.10",
            scan_type=ScanType.TCP_CONNECT,
            service_detection=False,
        )

        port = result["results"][0]["ports"][0]
        assert port["port_number"] == 443
        assert port["protocol"] == "tcp"

    async def test_udp_scan_labels_protocol_udp(self, scanner):
        scanner.port_scanner.udp_scan.return_value = {161: PortState.OPEN}

        result = await NetworkScanner.scan(
            scanner,
            target="192.168.1.10",
            scan_type=ScanType.UDP,
            service_detection=False,
        )

        port = result["results"][0]["ports"][0]
        assert port["port_number"] == 161
        assert port["protocol"] == "udp"

    async def test_no_active_hosts_returns_empty_result(self, scanner):
        scanner.network_mapper.parse_target.return_value = ["192.168.1.0/30"]
        scanner.network_mapper.discover_hosts.return_value = []

        result = await NetworkScanner.scan(
            scanner,
            target="192.168.1.0/30",
            scan_type=ScanType.TCP_CONNECT,
        )

        assert result == {
            "hosts_total": 1,
            "hosts_up": 0,
            "hosts_failed": 0,
            "total_ports_found": 0,
            "results": [],
        }
        scanner.port_scanner.tcp_connect_scan.assert_not_called()


class TestHostnameResolution:
    def test_disabled_resolution_skips_dns(self, scanner):
        with patch("app.core.scanner.socket.gethostbyaddr") as resolve:
            assert scanner._resolve_hostname("192.168.1.10") is None
            resolve.assert_not_called()

    def test_dns_failures_are_ignored(self, scanner):
        scanner.resolve_hostnames = True
        with patch(
            "app.core.scanner.socket.gethostbyaddr",
            side_effect=OSError("dns down"),
        ):
            assert scanner._resolve_hostname("192.168.1.10") is None

    def test_resolved_hostname_is_returned(self, scanner):
        scanner.resolve_hostnames = True
        with patch(
            "app.core.scanner.socket.gethostbyaddr",
            return_value=("router.local", [], ["192.168.1.10"]),
        ):
            assert scanner._resolve_hostname("192.168.1.10") == "router.local"
