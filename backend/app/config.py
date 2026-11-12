from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


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
    database_url: str = "postgresql://scanner:scanner123@db:5432/network_scanner"
    
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
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    
    @property
    def redis_url(self) -> str:
        """Get Redis URL"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()
