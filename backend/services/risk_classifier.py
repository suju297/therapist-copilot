"""Enhanced risk classifier with mental state assessment."""

import asyncio
import json
import logging
from typing import Dict, Any

from config import get_settings
from services.llm.llm_factory import get_risk_model
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

# Updated prompt with mental state assessment
RISK_ASSESSMENT_PROMPT = """
You are a mental-health triage assistant.

Return a JSON object **exactly** like this:

{{
  "risk_score": 0.0,               
  "risk_level": "low|medium|high|critical",
  "mental_state": "calm|stressed|anxious|depressed|suicidal",
  "top_emotions": ["sad", "guilty", "..."],
  "explanation": "...",
  "recommendations": ["..."]
}}

Guidelines:
- 0.00-0.30 → calm   / low
- 0.31-0.60 → stressed|anxious / medium
- 0.61-0.80 → depressed        / high
- 0.81-1.00 → suicidal         / critical

Transcript (last {window_seconds} s / ~{window_words} w):

{text}
"""

def _score_to_state(score: float) -> str:
    """Map risk score to mental state."""
    if score >= 0.81:
        return "suicidal"
    if score >= 0.61:
        return "depressed"
    if score >= 0.31:
        return "stressed"
    return "calm"

def _score_to_level(score: float) -> str:
    """Map risk score to risk level."""
    if score >= 0.81:
        return "critical"
    if score >= 0.61:
        return "high"
    if score >= 0.31:
        return "medium"
    return "low"

async def assess_risk_level(text: str, window_seconds: int = 45, window_words: int = 250) -> Dict[str, Any]:
    """
    Assess risk level and mental state from transcript text.
    
    Args:
        text: Transcript text to analyze
        window_seconds: Time window for context (for prompt)
        window_words: Word count for context (for prompt)
        
    Returns:
        Dict containing risk score, level, mental state, explanation, and recommendations
    """
    try:
        # Get settings and check if Gemini is configured
        settings = get_settings()
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not configured, using fallback risk assessment")
            return _fallback_risk_assessment(text)
        
        # Get the Gemini model
        model = get_risk_model()
        
        # Create the prompt with window context
        prompt = RISK_ASSESSMENT_PROMPT.format(
            text=text,
            window_seconds=window_seconds,
            window_words=window_words
        )
        
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
        required_fields = ["risk_score", "risk_level", "mental_state", "explanation"]
        for field in required_fields:
            if field not in result:
                logger.error(f"Missing required field: {field}")
                return _fallback_risk_assessment(text)
        
        # Ensure risk_score is within valid range
        result["risk_score"] = max(0.0, min(1.0, float(result["risk_score"])))
        
        # Auto-correct mental_state based on score if mismatch
        result["mental_state"] = _score_to_state(result["risk_score"])
        
        # Auto-correct risk_level based on score if mismatch
        result["risk_level"] = _score_to_level(result["risk_score"])
        
        # Ensure recommendations is a list
        if "recommendations" not in result:
            result["recommendations"] = []
        elif not isinstance(result["recommendations"], list):
            result["recommendations"] = [str(result["recommendations"])]
        
        # Ensure top_emotions is a list
        if "top_emotions" not in result:
            result["top_emotions"] = []
        elif not isinstance(result["top_emotions"], list):
            result["top_emotions"] = [str(result["top_emotions"])]
        
        logger.info(f"Risk assessment completed: {result['mental_state']} / {result['risk_level']} ({result['risk_score']:.2f})")
        return result
        
    except Exception as e:
        logger.error(f"Risk assessment failed: {e}")
        return _fallback_risk_assessment(text)


def _fallback_risk_assessment(text: str) -> Dict[str, Any]:
    """
    Fallback risk assessment using simple keyword matching.
    Enhanced with mental state detection.
    """
    text_lower = text.lower()
    
    # Crisis keywords (immediate high risk)
    crisis_keywords = [
        "kill myself", "end my life", "want to die", "suicide", "suicidal",
        "hurt myself", "self harm", "can't go on", "better off dead",
        "no point living", "end it all"
    ]
    
    # Depression keywords  
    depression_keywords = [
        "hopeless", "worthless", "useless", "failure", "depressed",
        "empty", "numb", "alone", "isolated", "burden"
    ]
    
    # Anxiety/stress keywords
    anxiety_keywords = [
        "anxious", "panic", "worried", "scared", "terrified",
        "overwhelmed", "stressed", "can't cope", "losing control"
    ]
    
    # Calculate scores
    crisis_score = sum(1 for keyword in crisis_keywords if keyword in text_lower)
    depression_score = sum(1 for keyword in depression_keywords if keyword in text_lower)
    anxiety_score = sum(1 for keyword in anxiety_keywords if keyword in text_lower)
    
    # Determine risk score
    if crisis_score > 0:
        risk_score = 0.85 + min(0.15, crisis_score * 0.05)
    elif depression_score >= 2:
        risk_score = 0.65 + min(0.15, depression_score * 0.05)
    elif anxiety_score >= 2:
        risk_score = 0.35 + min(0.25, anxiety_score * 0.05)
    elif depression_score >= 1 or anxiety_score >= 1:
        risk_score = 0.25 + min(0.20, (depression_score + anxiety_score) * 0.05)
    else:
        risk_score = 0.1
    
    # Cap at 1.0
    risk_score = min(1.0, risk_score)
    
    # Map to mental state and risk level
    mental_state = _score_to_state(risk_score)
    risk_level = _score_to_level(risk_score)
    
    # Generate explanation
    if crisis_score > 0:
        explanation = f"Crisis language detected: found {crisis_score} crisis indicators"
        recommendations = [
            "Immediate professional intervention recommended",
            "Contact emergency services if imminent danger",
            "Ensure client safety and supervision"
        ]
        emotions = ["despair", "hopeless", "suicidal"]
    elif depression_score >= 2:
        explanation = f"Multiple depression indicators detected: {depression_score} markers found"
        recommendations = [
            "Consider depression screening tools",
            "Explore mood tracking and behavioral interventions",
            "Monitor for worsening symptoms"
        ]
        emotions = ["sad", "hopeless", "empty"]
    elif anxiety_score >= 2:
        explanation = f"Elevated anxiety indicators: {anxiety_score} stress markers found"
        recommendations = [
            "Explore anxiety management techniques",
            "Consider relaxation and breathing exercises",
            "Identify triggers and coping strategies"
        ]
        emotions = ["anxious", "worried", "overwhelmed"]
    else:
        explanation = "No significant risk indicators detected in current text"
        recommendations = [
            "Continue supportive listening",
            "Maintain therapeutic rapport",
            "Monitor for changes"
        ]
        emotions = ["calm"]
    
    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "mental_state": mental_state,
        "top_emotions": emotions,
        "explanation": explanation,
        "recommendations": recommendations
    }