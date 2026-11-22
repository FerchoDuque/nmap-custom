from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"

VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class Settings(BaseSettings):
    """Application configuration settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Environment
    env: str = "development"
    
    # Database - PostgreSQL by default, SQLite for local dev
    database_url: str = "postgresql+psycopg2://scanner:scanner123@db:5432/network_scanner"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Scanning Configuration
    max_concurrent_scans: int = 5
    default_scan_timeout: int = 300
    max_ports_per_scan: int = 65535
    max_hosts_per_scan: int = 1024
    resolve_hostnames: bool = True
    
    # Security
    secret_key: str = DEFAULT_SECRET_KEY

    # Logging
    log_level: str = "INFO"

    # Schema and data lifecycle
    # `create_all` is kept for tests/local dev; production images run Alembic
    # in the entrypoint and set AUTO_CREATE_SCHEMA=false.
    auto_create_schema: bool = True
    # Delete finished scans older than this many days; 0 disables retention.
    data_retention_days: int = 30

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate the log level (e.g. ``debug`` → ``DEBUG``)."""
        level = str(value).strip().upper()
        if level not in VALID_LOG_LEVELS:
            raise ValueError(
                f"LOG_LEVEL must be one of {', '.join(sorted(VALID_LOG_LEVELS))}"
            )
        return level

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, values: List[str]) -> List[str]:
        """Require explicit origins; a wildcard would expose the API broadly."""
        origins = [origin.strip() for origin in values if origin.strip()]
        if not origins:
            raise ValueError("CORS_ORIGINS cannot be empty")
        if "*" in origins:
            raise ValueError("Wildcard CORS origins are not allowed")
        return origins

    @field_validator(
        "max_concurrent_scans",
        "max_hosts_per_scan",
        "max_ports_per_scan",
        "default_scan_timeout",
    )
    @classmethod
    def validate_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be a positive integer")
        return value

    @field_validator("data_retention_days")
    @classmethod
    def validate_retention_days(cls, value: int) -> int:
        if value < 0:
            raise ValueError("DATA_RETENTION_DAYS cannot be negative")
        return value

    @property
    def redis_url(self) -> str:
        """Get Redis URL"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def uses_default_secret(self) -> bool:
        """True when the placeholder secret has not been replaced."""
        return self.secret_key == DEFAULT_SECRET_KEY


# Global settings instance
settings = Settings()
