import ipaddress
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.network_mapper import NetworkMapper


class TestParseTarget:
    def test_single_ip(self):
        assert NetworkMapper.parse_target("192.168.1.10") == ["192.168.1.10"]

    def test_cidr(self):
        hosts = NetworkMapper.parse_target("192.168.1.0/30")
        assert hosts == ["192.168.1.1", "192.168.1.2"]

    def test_ip_range(self):
        hosts = NetworkMapper.parse_target("192.168.1.1-192.168.1.3")
        assert hosts == ["192.168.1.1", "192.168.1.2", "192.168.1.3"]

    def test_hostname_resolves(self):
        with patch("socket.gethostbyname", return_value="10.0.0.5"):
            assert NetworkMapper.parse_target("example.local") == ["10.0.0.5"]

    def test_invalid_target_returns_empty(self):
        with patch("socket.gethostbyname", side_effect=Exception("boom")):
            assert NetworkMapper.parse_target("not a valid target ???") == []


class TestGetNetworkInfo:
    def test_private_ipv4(self):
        info = NetworkMapper.get_network_info("192.168.1.1")
        assert info["ip"] == "192.168.1.1"
        assert info["version"] == "IPv4"
        assert info["is_private"] is True
        assert info["is_loopback"] is False

    def test_loopback(self):
        info = NetworkMapper.get_network_info("127.0.0.1")
        assert info["is_loopback"] is True

    def test_invalid_ip_returns_empty(self):
        assert NetworkMapper.get_network_info("not-an-ip") == {}


class TestDiscoverHosts:
    async def test_filters_active_hosts(self):
        mapper = NetworkMapper()

        async def fake_ping(host, timeout=0.1):
            return host.endswith(".2")

        with patch.object(NetworkMapper, "parse_target", return_value=["10.0.0.1", "10.0.0.2", "10.0.0.3"]), \
             patch.object(mapper, "_ping_host", side_effect=fake_ping):
            active = await mapper.discover_hosts("10.0.0.0/30")

        assert active == ["10.0.0.2"]
