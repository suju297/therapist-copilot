"""Routes package for Therapist Copilot API."""

# Import routers for easy access
from .health import router as health_router
from .stt import router as stt_router
from .risk_assessment import router as risk_router
from .ws_stream import router as ws_router

__all__ = [
    "health_router",
    "stt_router", 
    "risk_router",
    "ws_router"
]