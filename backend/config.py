"""Simplified configuration management for transcription and risk assessment only."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Find .env file in parent directory
backend_dir = Path(__file__).parent
parent_dir = backend_dir.parent
env_path = parent_dir / ".env"

# Force load .env file
load_dotenv(env_path)

# Debug logging
print(f"Loading .env from: {env_path}")
print(f"File exists: {env_path.exists()}")
print(f"ASSEMBLYAI_API_KEY from env: {os.getenv('ASSEMBLYAI_API_KEY', 'NOT FOUND')}")


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
    
    # Speech-to-Text Configuration
    stt_provider: str = Field(default="assemblyai", env="STT_PROVIDER")  # "assemblyai" or "whisper"
    
    # AssemblyAI Configuration
    assemblyai_api_key: str = Field(default="", env="ASSEMBLYAI_API_KEY")
    assemblyai_sample_rate: int = Field(default=16000, env="ASSEMBLYAI_SAMPLE_RATE")
    assemblyai_format_turns: bool = Field(default=True, env="ASSEMBLYAI_FORMAT_TURNS")
    
    # Deepgram Configuration (fallback)
    deepgram_api_key: str = Field(default="", env="DEEPGRAM_API_KEY")
    deepgram_model: str = Field(default="nova-2", env="DEEPGRAM_MODEL")
    deepgram_language: str = Field(default="en-US", env="DEEPGRAM_LANGUAGE")
    deepgram_encoding: str = Field(default="linear16", env="DEEPGRAM_ENCODING")
    deepgram_sample_rate: int = Field(default=16000, env="DEEPGRAM_SAMPLE_RATE")
    
    # Speech-to-Text (Whisper - fallback)
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
    audio_temp_dir: str = Field(default="/tmp/therapist_copilot", env="AUDIO_TEMP_DIR")
    session_timeout_hours: int = Field(default=24, env="SESSION_TIMEOUT_HOURS")
    
    @property
    def ws_chunk_samples(self) -> int:
        """Calculate samples per WebSocket chunk."""
        return int(self.audio_sample_rate * self.ws_chunk_ms / 1000)
    
    class Config:
        env_file = str(env_path)  # Use the absolute path
        env_file_encoding = "utf-8"
        # Also look for environment variables that are already set
        case_sensitive = False


# Global settings instance
settings = Settings()

# Debug print
print(f"Settings loaded - AssemblyAI API Key: {settings.assemblyai_api_key[:10]}..." if settings.assemblyai_api_key else "No AssemblyAI key!")


def get_settings() -> Settings:
    """Get application settings."""
    return settings