"""Simplified risk assessment using Gemini AI."""

import json
import logging
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

from config import get_settings

logger = logging.getLogger(__name__)


RISK_ASSESSMENT_PROMPT = """
You are a mental health risk assessment AI. Analyze the following therapy session transcript and provide a risk assessment.

IMPORTANT: Focus on identifying immediate safety concerns such as:
- Suicidal ideation or plans
- Self-harm behaviors
- Homicidal thoughts
- Severe psychosis or disconnection from reality
- Substance abuse with immediate danger
- Domestic violence or abuse situations

Rate the risk level from 0.0 to 1.0 where:
- 0.0-0.3: Low risk (general mental health concerns, mild anxiety/depression)
- 0.4-0.6: Medium risk (moderate symptoms, some concerning behaviors)
- 0.7-1.0: High risk (immediate safety concerns, requires intervention)

Provide your assessment in this exact JSON format:
{{
    "risk_score": <float between 0.0 and 1.0>,
    "risk_level": "<low|medium|high>",
    "explanation": "<brief explanation of the assessment>",
    "recommendations": ["<list of specific recommendations>"]
}}

Transcript to analyze:
{text}
"""


def get_risk_model() -> ChatGoogleGenerativeAI:
    """Get Gemini model for risk assessment."""
    settings = get_settings()
    
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is required for risk assessment")
    
    return ChatGoogleGenerativeAI(
        model=settings.llm_model_risk,
        google_api_key=settings.gemini_api_key,
        temperature=0.1,  # Low temperature for consistent risk assessment
        max_tokens=1024,
        safety_settings={
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE", 
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",  # Allow assessment of dangerous content
        }
    )


async def assess_risk_level(text: str) -> Dict[str, Any]:
    """
    Assess risk level of the given text using Gemini AI.
    
    Args:
        text: Transcript text to analyze
        
    Returns:
        Dict containing risk score, level, explanation, and recommendations
    """
    try:
        # Get settings and check if Gemini is configured
        settings = get_settings()
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not configured, using fallback risk assessment")
            return _fallback_risk_assessment(text)
        
        # Get the Gemini model
        model = get_risk_model()
        
        # Create the prompt
        prompt = RISK_ASSESSMENT_PROMPT.format(text=text)
        
        # Get response from Gemini
        message = HumanMessage(content=prompt)
        response = await model.ainvoke([message])
        
        # Parse the JSON response
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Raw response: {response.content}")
            return _fallback_risk_assessment(text)
        
        # Validate the response structure
        required_fields = ["risk_score", "risk_level", "explanation"]
        for field in required_fields:
            if field not in result:
                logger.error(f"Missing required field: {field}")
                return _fallback_risk_assessment(text)
        
        # Ensure risk_score is within valid range
        result["risk_score"] = max(0.0, min(1.0, float(result["risk_score"])))
        
        # Ensure risk_level matches score
        score = result["risk_score"]
        if score <= 0.3:
            result["risk_level"] = "low"
        elif score <= 0.6:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "high"
        
        # Ensure recommendations is a list
        if "recommendations" not in result:
            result["recommendations"] = []
        elif not isinstance(result["recommendations"], list):
            result["recommendations"] = [str(result["recommendations"])]
        
        logger.info(f"Risk assessment completed: {result['risk_level']} ({result['risk_score']:.2f})")
        return result
        
    except Exception as e:
        logger.error(f"Risk assessment failed: {e}")
        return _fallback_risk_assessment(text)


def _fallback_risk_assessment(text: str) -> Dict[str, Any]:
    """
    Fallback risk assessment using simple keyword matching.
    
    Args:
        text: Text to analyze
        
    Returns:
        Basic risk assessment result
    """
    try:
        # Simple keyword-based risk assessment
        high_risk_keywords = [
            "kill myself", "suicide", "end it all", "don't want to live",
            "hurt myself", "cut myself", "overdose", "jump off",
            "kill someone", "hurt others", "violent thoughts"
        ]
        
        medium_risk_keywords = [
            "hopeless", "worthless", "trapped", "burden",
            "can't go on", "overwhelmed", "desperate",
            "angry", "rage", "hate everyone"
        ]
        
        text_lower = text.lower()
        
        # Count keyword matches
        high_risk_count = sum(1 for keyword in high_risk_keywords if keyword in text_lower)
        medium_risk_count = sum(1 for keyword in medium_risk_keywords if keyword in text_lower)
        
        # Calculate risk score
        risk_score = 0.1  # Base risk
        risk_score += high_risk_count * 0.3  # High risk keywords add more
        risk_score += medium_risk_count * 0.1  # Medium risk keywords add less
        risk_score = min(1.0, risk_score)  # Cap at 1.0
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "high"
            explanation = f"High-risk language detected ({high_risk_count} high-risk keywords)"
            recommendations = ["Immediate professional intervention recommended", "Contact crisis hotline"]
        elif risk_score >= 0.4:
            risk_level = "medium"
            explanation = f"Moderate risk indicators present ({medium_risk_count} concerning keywords)"
            recommendations = ["Monitor closely", "Consider professional consultation"]
        else:
            risk_level = "low"
            explanation = "No significant risk indicators detected"
            recommendations = ["Continue standard care"]
        
        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "explanation": explanation,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Fallback risk assessment failed: {e}")
        # Ultimate fallback
        return {
            "risk_score": 0.5,
            "risk_level": "medium",
            "explanation": f"Risk assessment error: {str(e)}",
            "recommendations": ["Manual review required due to assessment error"]
        }