"""Risk assessment endpoints."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.risk_classifier import assess_risk_level

logger = logging.getLogger(__name__)
router = APIRouter()


class RiskAssessmentRequest(BaseModel):
    """Request model for risk assessment."""
    text: str


class RiskAssessmentResponse(BaseModel):
    """Response model for risk assessment."""
    risk_score: float
    risk_level: str
    explanation: str
    recommendations: list


@router.post("/assess", response_model=RiskAssessmentResponse)
async def assess_risk(request: RiskAssessmentRequest):
    """
    Assess risk level of the given text.
    
    Args:
        request: Risk assessment request containing text to analyze
        
    Returns:
        Risk assessment result with score, level, and recommendations
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        logger.info(f"Assessing risk for text: {request.text[:100]}...")
        
        # Perform risk assessment
        result = await assess_risk_level(request.text.strip())
        
        logger.info(f"Risk assessment completed: {result['risk_level']} ({result['risk_score']:.2f})")
        
        return RiskAssessmentResponse(
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            explanation=result["explanation"],
            recommendations=result.get("recommendations", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk assessment failed: {e}")
        # Return medium risk as a safe fallback
        return RiskAssessmentResponse(
            risk_score=0.5,
            risk_level="medium",
            explanation=f"Risk assessment error: {str(e)}",
            recommendations=["Manual review required due to assessment error"]
        )


@router.get("/status")
async def get_risk_assessment_status():
    """Get risk assessment service status."""
    from config import get_settings
    
    settings = get_settings()
    
    # Check if Gemini API is configured
    gemini_configured = bool(settings.gemini_api_key and len(settings.gemini_api_key) > 10)
    
    return {
        "service_available": gemini_configured,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model_risk,
        "risk_threshold": settings.risk_threshold,
        "status": "configured" if gemini_configured else "not_configured",
        "warnings": [] if gemini_configured else ["Gemini API key not configured"]
    }