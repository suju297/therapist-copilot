"""Routes package for Therapist Copilot API."""

# Import routers for easy access
from .health import router as health_router
from .stt import router as stt_router
from .ws_stream import router as ws_router

# Try to import risk assessment router, create fallback if not exists
try:
    from .risk_assessment import router as risk_router
except ImportError:
    # Create a simple fallback router if risk_assessment.py doesn't exist
    from fastapi import APIRouter
    risk_router = APIRouter()

__all__ = [
    "health_router",
    "stt_router", 
    "risk_router",
    "ws_router"
]