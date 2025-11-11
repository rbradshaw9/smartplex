"""
Configuration management for SmartPlex API using Pydantic settings.
Loads environment variables and provides typed configuration objects.
"""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application settings
    app_name: str = Field(default="SmartPlex API", alias="APP_NAME")
    environment: str = Field(default="development", alias="SMARTPLEX_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # Supabase configuration
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_service_key: str = Field(..., alias="SUPABASE_SERVICE_KEY")
    supabase_anon_key: Optional[str] = Field(default=None, alias="SUPABASE_ANON_KEY")
    
    # Frontend configuration
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    
    # AI/LLM configuration
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    
    # Monitoring & Error Tracking
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    
    # Redis configuration  
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    
    # External API configuration
    plex_client_id: Optional[str] = Field(default=None, alias="PLEX_CLIENT_ID")
    plex_client_secret: Optional[str] = Field(default=None, alias="PLEX_CLIENT_SECRET")
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    class Config:
        """Pydantic config for settings."""
        env_file = ".env"
        case_sensitive = False


# Create a singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings