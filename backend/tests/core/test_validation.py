import pytest

from app.core.validation import (
    normalize_port_range,
    normalize_scan_config,
    normalize_target,
)


class TestNormalizeTarget:
    @pytest.mark.parametrize(
        "value",
        [
            "192.168.1.10",
            " 10.0.0.0/24 ",
            "localhost",
            "scan-01.example.com",
            "2001:db8::1",
            "2001:db8::/120",
            "192.168.1.10-192.168.1.20",
        ],
    )
    def test_accepts_supported_targets(self, value):
        assert normalize_target(value) == value.strip()

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "   ",
            "999.1.1.1",
            "10.0.0.0/33",
            "2001:db8::/129",
            "bad_host",
            "-bad.example.com",
            "bad..example.com",
            "192.168.1.20-192.168.1.10",
            "192.168.1.1-2001:db8::1",
            "not a target",
        ],
    )
    def test_rejects_invalid_targets(self, value):
        with pytest.raises(ValueError):
            normalize_target(value)

    def test_rejects_non_string_values(self):
        with pytest.raises(ValueError):
            normalize_target(None)

    @pytest.mark.parametrize(
        "value",
        ["10.0.0.0/8", "2001:db8::/32", "10.0.0.1-10.1.0.1"],
    )
    def test_rejects_ranges_above_host_limit(self, value):
        with pytest.raises(ValueError, match="exceeds maximum of 1024 hosts"):
            normalize_target(value)


class TestNormalizePortRange:
    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_accepts_empty_range(self, value):
        assert normalize_port_range(value) is None

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("22,80,443", "22,80,443"),
            (" 1-1000 ", "1-1000"),
            ("22, 100-200,443", "22,100-200,443"),
        ],
    )
    def test_accepts_and_normalizes_valid_ranges(self, value, expected):
        assert normalize_port_range(value) == expected

    @pytest.mark.parametrize(
        "value",
        ["0-100", "70000", "100-50", "abc", "22,,80", "22-", "1.5-2"],
    )
    def test_rejects_invalid_ranges(self, value):
        with pytest.raises(ValueError):
            normalize_port_range(value)

    def test_rejects_ranges_above_port_limit(self):
        with pytest.raises(ValueError, match="exceeds maximum of 500 ports"):
            normalize_port_range("1-1000", max_ports=500)

    def test_accepts_ranges_within_custom_limit(self):
        assert normalize_port_range("1-100", max_ports=100) == "1-100"


class TestNormalizeScanConfig:
    def test_normalizes_and_keeps_extra_keys(self):
        config = normalize_scan_config(
            {
                "target": " 192.168.1.0/24 ",
                "scan_type": "udp",
                "port_range": "53, 123",
                "custom": "kept",
            }
        )

        assert config == {
            "target": "192.168.1.0/24",
            "scan_type": "udp",
            "port_range": "53,123",
            "custom": "kept",
        }

    def test_defaults_are_not_injected(self):
        assert normalize_scan_config({"target": "10.0.0.1"}) == {
            "target": "10.0.0.1"
        }

    @pytest.mark.parametrize(
        "config",
        [
            {},
            {"target": ""},
            {"target": "999.1.1.1"},
            {"target": "10.0.0.1", "scan_type": "invalid"},
            {"target": "10.0.0.1", "port_range": "70000"},
        ],
    )
    def test_rejects_invalid_configuration(self, config):
        with pytest.raises(ValueError):
            normalize_scan_config(config)

    def test_rejects_non_dict(self):
        with pytest.raises(ValueError):
            normalize_scan_config(["target", "10.0.0.1"])
