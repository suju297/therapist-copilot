"""Simplified configuration management for transcription and risk assessment only."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="Therapist Copilot API", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Gemini API Configuration
    llm_provider: str = Field(default="gemini", env="LLM_PROVIDER")
    llm_model_risk: str = Field(default="gemini-2.0-flash-exp", env="LLM_MODEL_RISK")
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    
    # Speech-to-Text (Deepgram)
    stt_provider: str = Field(default="deepgram", env="STT_PROVIDER")
    deepgram_api_key: str = Field(default="", env="DEEPGRAM_API_KEY")
    deepgram_model: str = Field(default="nova-2", env="DEEPGRAM_MODEL")
    deepgram_language: str = Field(default="en", env="DEEPGRAM_LANGUAGE")
    
    # Legacy Whisper settings (for backward compatibility)
    whisper_model_size: str = Field(default="base", env="WHISPER_MODEL_SIZE")
    
    # Audio/WebSocket
    audio_sample_rate: int = Field(default=16000, env="AUDIO_SAMPLE_RATE")
    ws_chunk_ms: int = Field(default=1000, env="WS_CHUNK_MS")
    
    # Risk Assessment
    risk_threshold: float = Field(default=0.5, env="RISK_THRESHOLD")
    
    # Security/Auth
    therapist_token: str = Field(default="supersecret-dev-token", env="THERAPIST_TOKEN")
    secret_key: str = Field(default="replace-me", env="SECRET_KEY")
    
    # File & Temporary Storage
    audio_temp_dir: str = Field(default="C:\\temp\\therapist_copilot", env="AUDIO_TEMP_DIR")
    session_timeout_hours: int = Field(default=24, env="SESSION_TIMEOUT_HOURS")
    
    # Validators to clean up values with inline comments
    @validator('debug', pre=True)
    def parse_debug(cls, v):
        if isinstance(v, str):
            v = v.split('#')[0].strip().lower()
            return v in ('true', '1', 'yes', 'on')
        return v
    
    @validator('audio_sample_rate', 'ws_chunk_ms', 'port', 'session_timeout_hours', pre=True)
    def parse_int(cls, v):
        if isinstance(v, str):
            v = v.split('#')[0].strip()
        return int(v)
    
    @validator('risk_threshold', pre=True)
    def parse_float(cls, v):
        if isinstance(v, str):
            v = v.split('#')[0].strip()
        return float(v)
    
    @validator('*', pre=True)
    def strip_comments(cls, v):
        if isinstance(v, str) and '#' in v:
            v = v.split('#')[0].strip()
        return v
    
    @property
    def ws_chunk_samples(self) -> int:
        """Calculate samples per WebSocket chunk."""
        return int(self.audio_sample_rate * self.ws_chunk_ms / 1000)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings