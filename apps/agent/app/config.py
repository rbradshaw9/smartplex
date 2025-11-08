"""
Configuration management for SmartPlex Agent.
Environment-specific settings for local Plex server automation.
"""

import os
from functools import lru_cache
from typing import Optional, List

from pydantic import Field
from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    """Agent-specific settings loaded from environment variables."""
    
    # Application settings
    app_name: str = Field(default="SmartPlex Agent", alias="APP_NAME")
    environment: str = Field(default="development", alias="SMARTPLEX_ENV")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # SmartPlex API connection
    smartplex_api_url: str = Field(default="http://localhost:8000", alias="SMARTPLEX_API_URL")
    smartplex_api_token: Optional[str] = Field(default=None, alias="SMARTPLEX_API_TOKEN")
    agent_id: str = Field(default="agent-localhost", alias="AGENT_ID")
    
    # Plex server configuration
    plex_url: str = Field(default="http://localhost:32400", alias="PLEX_URL")
    plex_token: str = Field(..., alias="PLEX_TOKEN")
    plex_library_paths: List[str] = Field(default=["/data/media"], alias="PLEX_LIBRARY_PATHS")
    
    # Storage and cleanup settings
    storage_threshold_warning: int = Field(default=85, alias="STORAGE_THRESHOLD_WARNING")
    storage_threshold_critical: int = Field(default=95, alias="STORAGE_THRESHOLD_CRITICAL")
    cleanup_enabled: bool = Field(default=False, alias="CLEANUP_ENABLED")
    cleanup_dry_run: bool = Field(default=True, alias="CLEANUP_DRY_RUN")
    
    # Automation schedules (cron expressions)
    heartbeat_interval: int = Field(default=300, alias="HEARTBEAT_INTERVAL_SECONDS")  # 5 minutes
    storage_check_cron: str = Field(default="0 */6 * * *", alias="STORAGE_CHECK_CRON")  # Every 6 hours
    cleanup_check_cron: str = Field(default="0 2 * * *", alias="CLEANUP_CHECK_CRON")  # Daily at 2 AM
    
    # Security
    api_key: str = Field(default="dev-agent-key", alias="AGENT_API_KEY")
    
    class Config:
        """Pydantic config for settings."""
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> AgentSettings:
    """Get cached agent settings."""
    return AgentSettings()