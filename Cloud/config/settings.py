import os
from pydantic import BaseModel, Field


class CloudSettings(BaseModel):
    app_name: str = "JARVIS Cloud Platform"
    version: str = "1.0.0"
    environment: str = Field(default_factory=lambda: os.getenv("JARVIS_ENV", "development"))
    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///logs/jarvis_cloud_dev.db"))
    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "jarvis_cloud_super_secret_jwt_key_32bytes"))
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    rate_limit_per_minute: int = 100
    host: str = Field(default_factory=lambda: os.getenv("CLOUD_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: os.getenv("CLOUD_PORT", "8001"))


cloud_settings = CloudSettings()
