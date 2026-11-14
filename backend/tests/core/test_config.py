import pytest
from pydantic import ValidationError

from app.config import DEFAULT_SECRET_KEY, Settings


def _settings(**overrides):
    values = {
        "database_url": "sqlite://",
        "cors_origins": ["http://localhost:5173"],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class TestCorsSettings:
    def test_accepts_explicit_origins_and_strips_whitespace(self):
        settings = _settings(
            cors_origins=[" http://localhost:5173 ", "https://scanner.local"]
        )
        assert settings.cors_origins == [
            "http://localhost:5173",
            "https://scanner.local",
        ]

    def test_rejects_wildcard_origin(self):
        with pytest.raises(ValidationError, match="Wildcard CORS origins"):
            _settings(cors_origins=["*"])

    def test_rejects_empty_origin_list(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            _settings(cors_origins=["  "])


class TestResourceLimits:
    @pytest.mark.parametrize(
        "field",
        [
            "max_concurrent_scans",
            "max_hosts_per_scan",
            "max_ports_per_scan",
            "default_scan_timeout",
        ],
    )
    def test_rejects_non_positive_limits(self, field):
        with pytest.raises(ValidationError):
            _settings(**{field: 0})

    def test_accepts_custom_limits(self):
        settings = _settings(
            max_concurrent_scans=2,
            max_hosts_per_scan=256,
            max_ports_per_scan=1000,
            default_scan_timeout=60,
        )
        assert settings.max_hosts_per_scan == 256
        assert settings.max_ports_per_scan == 1000


class TestLogLevel:
    def test_defaults_to_info(self):
        assert _settings().log_level == "INFO"

    def test_normalizes_lowercase_and_whitespace(self):
        assert _settings(log_level=" debug ").log_level == "DEBUG"

    @pytest.mark.parametrize("level", ["verbose", "TRACE", "10", ""])
    def test_rejects_unknown_levels(self, level):
        with pytest.raises(ValidationError, match="LOG_LEVEL"):
            _settings(log_level=level)


class TestSecretHandling:
    def test_flags_default_secret(self):
        assert _settings().uses_default_secret is True
        assert _settings(secret_key=DEFAULT_SECRET_KEY).uses_default_secret is True

    def test_accepts_replaced_secret(self):
        settings = _settings(secret_key="a" * 64)
        assert settings.uses_default_secret is False
