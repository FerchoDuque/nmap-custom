import asyncio
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.port_scanner import PortScanner
from app.models.scan import PortState


class TestParsePortRange:
    def test_default_when_none(self):
        ports = PortScanner.parse_port_range(None)
        assert ports == [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 8080, 8443]

    def test_single_ports_and_ranges(self):
        ports = PortScanner.parse_port_range("80,443,1000-1002, 22")
        assert ports == [22, 80, 443, 1000, 1001, 1002]

    def test_deduplicates_and_sorts(self):
        ports = PortScanner.parse_port_range("80,22,80,20-22")
        assert ports == [20, 21, 22, 80]

    def test_invalid_parts_are_ignored(self):
        ports = PortScanner.parse_port_range("80,abc,70000,5-3,443")
        assert ports == [80, 443]


class TestTcpConnectScan:
    async def test_open_closed_filtered_and_unknown(self):
        scanner = PortScanner(timeout=0.01)

        outcomes = {
            22: 0,  # open
            23: 111,  # closed
            24: socket.timeout(),  # filtered
            25: socket.error("boom"),  # filtered
            26: RuntimeError("unexpected"),  # unknown
        }
        sockets = {}

        def socket_factory(*args, **kwargs):
            m = MagicMock()

            def connect_ex(addr):
                host, port = addr
                val = outcomes[port]
                if isinstance(val, Exception):
                    raise val
                return val

            m.connect_ex.side_effect = connect_ex
            sockets.setdefault(args, m)
            return m

        async def fast_sleep(_):
            return None

        with patch("app.core.port_scanner.socket.socket", side_effect=socket_factory), \
             patch("app.core.port_scanner.asyncio.sleep", side_effect=fast_sleep):
            results = await scanner.tcp_connect_scan("127.0.0.1", [22, 23, 24, 25, 26])

        assert results[22] == PortState.OPEN
        assert results[23] == PortState.CLOSED
        assert results[24] == PortState.FILTERED
        assert results[25] == PortState.FILTERED
        assert results[26] == PortState.UNKNOWN


class TestUdpScan:
    async def test_open_on_response_open_on_timeout_closed_on_error(self):
        scanner = PortScanner(timeout=0.01)

        def make_sock(behavior):
            m = MagicMock()
            if behavior == "response":
                m.recvfrom.return_value = (b"data", ("h", 1))
            elif behavior == "timeout":
                m.recvfrom.side_effect = socket.timeout()
            elif behavior == "closed":
                m.recvfrom.side_effect = socket.error("unreachable")
            elif behavior == "unknown":
                m.sendto.side_effect = RuntimeError("boom")
            return m

        socks = {
            53: make_sock("response"),
            123: make_sock("timeout"),
            161: make_sock("closed"),
            162: make_sock("unknown"),
        }

        def socket_factory(*args, **kwargs):
            # return the mock for the port being scanned by tracking call order via sendto target
            # simpler: return a proxy that selects based on last sendto/recv context using mutable holder
            holder = {"port": None}
            m = MagicMock()

            def sendto(data, addr):
                holder["port"] = addr[1]
                real = socks[holder["port"]]
                return real.sendto(data, addr)

            def recvfrom(n):
                real = socks[holder["port"]]
                return real.recvfrom(n)

            m.sendto.side_effect = sendto
            m.recvfrom.side_effect = recvfrom
            return m

        async def fast_sleep(_):
            return None

        with patch("app.core.port_scanner.socket.socket", side_effect=socket_factory), \
             patch("app.core.port_scanner.asyncio.sleep", side_effect=fast_sleep):
            results = await scanner.udp_scan("127.0.0.1", [53, 123, 161, 162])

        assert results[53] == PortState.OPEN
        assert results[123] == PortState.OPEN  # current heuristic: timeout -> open
        assert results[161] == PortState.CLOSED
        assert results[162] == PortState.UNKNOWN
