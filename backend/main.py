"""Simplified FastAPI application for transcription and risk assessment."""

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
    """Application lifespan manager."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name}")
    
    # Create audio temp directory
    os.makedirs(settings.audio_temp_dir, exist_ok=True)
    logger.info(f"Audio temp directory: {settings.audio_temp_dir}")
    
    # Initialize STT service based on provider
    try:
        if settings.stt_provider == "assemblyai":
            from services.assemblyai_service import get_assemblyai_service
            assemblyai_service = get_assemblyai_service()
            if assemblyai_service.is_available():
                logger.info("AssemblyAI service initialized successfully")
            else:
                logger.warning("AssemblyAI service initialization failed - check API key")
        elif settings.stt_provider == "deepgram":
            from services.deepgram_service import get_deepgram_service
            deepgram_service = get_deepgram_service()
            if deepgram_service.is_available():
                logger.info("Deepgram service initialized successfully")
            else:
                logger.warning("Deepgram service initialization failed - check API key")
        else:
            from services.stt_adapter import get_stt_adapter
            stt_adapter = get_stt_adapter()
            if stt_adapter.is_available():
                logger.info(f"STT service ({settings.stt_provider}) initialized successfully")
            else:
                logger.warning(f"STT service ({settings.stt_provider}) initialization failed")
    except Exception as e:
        logger.error(f"Failed to initialize STT service: {e}")
    
    # Initialize Gemini for risk assessment
    try:
        if settings.gemini_api_key:
            logger.info("Gemini API key configured for risk assessment")
        else:
            logger.warning("Gemini API key not configured - risk assessment will fail")
    except Exception as e:
        logger.error(f"Error checking Gemini configuration: {e}")
    
    yield
    
    # Cleanup on shutdown
    try:
        if settings.stt_provider == "assemblyai":
            from services.assemblyai_service import get_assemblyai_service
            assemblyai_service = get_assemblyai_service()
            await assemblyai_service.cleanup_all_connections()
            logger.info("Cleaned up AssemblyAI connections")
        elif settings.stt_provider == "deepgram":
            from services.deepgram_service import get_deepgram_service
            deepgram_service = get_deepgram_service()
            await deepgram_service.cleanup_all_connections()
            logger.info("Cleaned up Deepgram connections")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="AI-powered transcription and risk assessment for therapy sessions",
        version="1.0.0",
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
    
    # Include all necessary routes
    from routes import health, stt, ws_stream
    
    # Create risk assessment router if it doesn't exist
    try:
        from routes import risk_assessment
        app.include_router(risk_assessment.router, prefix="/api/v1/risk", tags=["Risk Assessment"])
    except ImportError:
        # Create a simple risk assessment route if the module doesn't exist
        from fastapi import APIRouter
        from pydantic import BaseModel
        from services.risk_classifier import assess_risk_level
        
        risk_router = APIRouter()
        
        class RiskAssessmentRequest(BaseModel):
            text: str
        
        @risk_router.post("/assess")
        async def assess_risk(request: RiskAssessmentRequest):
            """Assess risk level of the given text."""
            try:
                result = await assess_risk_level(request.text)
                return result
            except Exception as e:
                logger.error(f"Risk assessment failed: {e}")
                return {
                    "risk_score": 0.5,
                    "risk_level": "medium",
                    "explanation": f"Risk assessment error: {str(e)}",
                    "recommendations": ["Manual review required due to assessment error"]
                }
        
        app.include_router(risk_router, prefix="/api/v1/risk", tags=["Risk Assessment"])
    
    # Include other routes
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(stt.router, prefix="/api/v1/stt", tags=["Speech-to-Text"])
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
        return {
            "message": f"Welcome to {settings.app_name}",
            "version": "1.0.0",
            "stt_provider": settings.stt_provider,
            "status": "running"
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