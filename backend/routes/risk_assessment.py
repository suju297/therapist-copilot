"""Risk assessment endpoints for therapy sessions."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.risk_classifier import assess_risk_level
from config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class RiskAssessmentRequest(BaseModel):
    """Request model for risk assessment."""
    text: str = Field(..., description="Transcript text to assess for risk")
    context: str = Field(default="", description="Additional context for assessment")


class RiskAssessmentResponse(BaseModel):
    """Response model for risk assessment."""
    risk_score: float = Field(..., description="Risk score from 0.0 to 1.0")
    risk_level: str = Field(..., description="Risk level: low, medium, or high")
    explanation: str = Field(..., description="Explanation of the risk assessment")
    recommendations: list = Field(default=[], description="List of recommendations")
    immediate_action_required: bool = Field(default=False, description="Whether immediate action is required")


@router.post("/assess", response_model=RiskAssessmentResponse)
async def assess_risk(request: RiskAssessmentRequest):
    """
    Assess risk level of given transcript text.
    
    Args:
        request: Risk assessment request containing text to analyze
        
    Returns:
        Risk assessment result with score, level, and recommendations
    """
    try:
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Combine text and context if provided
        full_text = request.text
        if request.context:
            full_text = f"{request.context}\n\n{request.text}"
        
        logger.info(f"Performing risk assessment on text: {request.text[:100]}...")
        
        # Perform risk assessment
        result = await assess_risk_level(full_text)
        
        # Check if assessment was successful
        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Risk assessment failed: {result['error']}")
        
        response = RiskAssessmentResponse(
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            explanation=result["explanation"],
            recommendations=result.get("recommendations", []),
            immediate_action_required=result["risk_score"] >= settings.risk_threshold
        )
        
        logger.info(f"Risk assessment completed: {response.risk_level} ({response.risk_score:.2f})")
        
        # Log high-risk assessments
        if response.risk_score >= settings.risk_threshold:
            logger.warning(f"HIGH RISK DETECTED: Score {response.risk_score:.2f} - {response.explanation}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk assessment endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Risk assessment service error")


@router.get("/threshold")
async def get_risk_threshold():
    """Get current risk threshold configuration."""
    return {
        "risk_threshold": settings.risk_threshold,
        "description": "Scores at or above this threshold are considered high risk",
        "levels": {
            "low": "0.0 - 0.3",
            "medium": "0.4 - 0.6", 
            "high": "0.7 - 1.0"
        }
    }


@router.get("/status")
async def get_risk_service_status():
    """Get risk assessment service status."""
    try:
        # Test the service with a simple, safe text
        test_result = await assess_risk_level("I feel good today.")
        service_available = "error" not in test_result
        
        return {
            "service_available": service_available,
            "risk_threshold": settings.risk_threshold,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model_risk,
            "gemini_configured": bool(settings.gemini_api_key),
            "test_result": test_result if service_available else None
        }
        
    except Exception as e:
        logger.error(f"Risk service status check failed: {e}")
        return {
            "service_available": False,
            "error": str(e),
            "risk_threshold": settings.risk_threshold,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model_risk,
            "gemini_configured": bool(settings.gemini_api_key)
        }