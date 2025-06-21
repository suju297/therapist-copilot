"""Enhanced FastAPI application with Deepgram integration for transcription and risk assessment."""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings


# Configure logging
logging.basicConfig(
    level=getattr(logging, get_settings().log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager with enhanced STT service initialization."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name}")
    
    # Create audio temp directory
    os.makedirs(settings.audio_temp_dir, exist_ok=True)
    logger.info(f"Audio temp directory: {settings.audio_temp_dir}")
    
    # Initialize STT services
    try:
        from services.stt_adapter import get_stt_service
        stt_service = get_stt_service()
        
        if stt_service.is_available():
            active_provider = stt_service.get_active_provider()
            logger.info(f"STT service initialized successfully with provider: {active_provider}")
            
            # Log service capabilities
            service_info = stt_service.get_service_info()
            logger.info(f"Available STT services: {[svc.get('provider', 'unknown') for svc in service_info['available_services']]}")
        else:
            logger.warning("No STT service available - please configure Deepgram API key or Whisper model")
            
    except Exception as e:
        logger.error(f"Failed to initialize STT services: {e}")
    
    # Initialize risk assessment service
    try:
        from services.risk_classifier import assess_risk_level
        # Test with a simple phrase
        test_result = await assess_risk_level("I feel okay today.")
        if "error" not in test_result:
            logger.info("Risk assessment service initialized successfully")
        else:
            logger.warning(f"Risk assessment service error: {test_result['error']}")
    except Exception as e:
        logger.error(f"Failed to initialize risk assessment service: {e}")
    
    yield
    
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered transcription and risk assessment for therapy sessions with Deepgram integration",
        version="2.0.0",
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    from routes import health, stt, ws_stream
    from routes.risk_assessment import router as risk_router
    
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(stt.router, prefix="/api/v1/stt", tags=["Speech-to-Text"])
    app.include_router(risk_router, prefix="/api/v1/risk", tags=["Risk Assessment"])
    app.include_router(ws_stream.router, prefix="/api/v1", tags=["WebSocket Audio Stream"])
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Global exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        settings = get_settings()
        from services.stt_adapter import get_stt_service
        
        stt_service = get_stt_service()
        active_provider = stt_service.get_active_provider()
        
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": "2.0.0",
            "features": [
                "Real-time audio transcription",
                "Multi-provider STT support (Deepgram, Whisper)",
                "Risk assessment and crisis detection",
                "WebSocket streaming",
                "File upload transcription"
            ],
            "stt_provider": active_provider,
            "endpoints": {
                "health": "/api/v1/health",
                "transcribe_file": "/api/v1/stt/transcribe",
                "assess_risk": "/api/v1/risk/assess",
                "websocket_stream": "/api/v1/ws/audio/{session_id}",
                "api_docs": "/docs"
            }
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )