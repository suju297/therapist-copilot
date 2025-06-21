"""Prompt templates for LLM interactions."""

from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.schema import SystemMessage, HumanMessage


# SOAP Note Generation Template
SOAP_GENERATION_TEMPLATE = """You are an expert clinical psychologist assistant helping to create SOAP notes from therapy session transcripts.

Given the following therapy session transcript and relevant CBT interventions, create a structured SOAP note and suggest appropriate homework assignments.

SESSION TRANSCRIPT:
{transcript}

RELEVANT CBT INTERVENTIONS:
{cbt_snippets}

INSTRUCTIONS:
1. Create a comprehensive SOAP note with the following sections:
   - Subjective: Patient's reported experiences, emotions, and concerns
   - Objective: Observable behaviors, mood, and clinical observations
   - Assessment: Clinical impressions, progress notes, and therapeutic insights
   - Plan: Treatment recommendations and next steps

2. Suggest 1-3 appropriate homework assignments based on:
   - The session content and patient needs
   - The relevant CBT interventions provided
   - Patient's current therapeutic goals

3. Format your response as valid JSON with this structure:
{{
  "soap_note": {{
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": "..."
  }},
  "homework_assignments": [
    {{
      "title": "...",
      "description": "...",
      "category": "...",
      "priority": "high|medium|low",
      "estimated_duration": 15,
      "instructions": "..."
    }}
  ],
  "clinical_insights": {{
    "primary_themes": ["..."],
    "therapeutic_techniques_used": ["..."],
    "patient_engagement_level": "high|medium|low",
    "session_effectiveness": "high|medium|low"
  }}
}}

Important guidelines:
- Keep all content professional and clinically appropriate
- Focus on therapeutic progress and evidence-based interventions
- Ensure homework assignments are realistic and achievable
- Maintain patient confidentiality (all names should already be de-identified)
- Use specific, actionable language in the Plan section
"""

SOAP_PROMPT = ChatPromptTemplate.from_template(SOAP_GENERATION_TEMPLATE)


# Risk Assessment Template
RISK_ASSESSMENT_TEMPLATE = """You are a clinical risk assessment specialist. Analyze the following therapy session transcript for potential risk indicators.

TRANSCRIPT:
{transcript}

Assess the risk level for the following categories:
- Suicide risk
- Self-harm risk
- Harm to others risk
- Substance abuse risk
- Crisis intervention needs

Provide your assessment as a JSON response with this structure:
{{
  "overall_risk_score": 0.0,
  "risk_categories": {{
    "suicide_risk": {{"score": 0.0, "indicators": ["..."]}},
    "self_harm_risk": {{"score": 0.0, "indicators": ["..."]}},
    "harm_to_others": {{"score": 0.0, "indicators": ["..."]}},
    "substance_abuse": {{"score": 0.0, "indicators": ["..."]}},
    "crisis_intervention": {{"score": 0.0, "indicators": ["..."]}}
  }},
  "recommendations": [
    "..."
  ],
  "immediate_action_required": false,
  "crisis_keywords_detected": ["..."]
}}

Risk scoring:
- 0.0-0.2: Low risk
- 0.3-0.4: Mild risk  
- 0.5-0.7: Moderate risk
- 0.8-1.0: High risk

Focus on explicit indicators and concerning language patterns. Be conservative in your assessment.
"""

RISK_ASSESSMENT_PROMPT = ChatPromptTemplate.from_template(RISK_ASSESSMENT_TEMPLATE)


# Deidentification Template
DEIDENTIFICATION_TEMPLATE = """Remove or replace all personally identifiable information (PII) from the following therapy session transcript while preserving the clinical context and therapeutic content.

Replace the following with generic placeholders:
- Names (people, places, organizations) → [NAME], [PLACE], [ORGANIZATION]
- Phone numbers → [PHONE]
- Email addresses → [EMAIL]
- Addresses → [ADDRESS]
- Dates (specific) → [DATE]
- Ages (specific) → [AGE]
- Professions/employers → [PROFESSION]/[EMPLOYER]
- Medical record numbers → [MRN]
- Insurance information → [INSURANCE]

Preserve:
- General timeframes (e.g., "last week", "yesterday")
- Therapeutic content and emotional expressions
- Clinical observations and symptoms
- Relationship dynamics (e.g., "my partner", "my mother")

TRANSCRIPT:
{transcript}

DEIDENTIFIED TRANSCRIPT:
"""

DEIDENTIFICATION_PROMPT = PromptTemplate(
    input_variables=["transcript"],
    template=DEIDENTIFICATION_TEMPLATE
)


# Homework Generation Template
HOMEWORK_GENERATION_TEMPLATE = """Based on the therapy session content and patient needs, suggest appropriate therapeutic homework assignments.

SESSION CONTEXT:
{session_context}

PATIENT FOCUS AREAS:
{focus_areas}

AVAILABLE CBT TECHNIQUES:
{cbt_techniques}

Generate 2-3 homework assignments that are:
1. Tailored to the patient's current therapeutic goals
2. Appropriate for their skill level and engagement
3. Evidence-based and therapeutically sound
4. Realistic and achievable

Format as JSON:
{{
  "assignments": [
    {{
      "title": "...",
      "description": "...",
      "category": "mindfulness|cbt|behavioral|journaling|skills_practice",
      "priority": "high|medium|low",
      "estimated_duration": 15,
      "instructions": "Step-by-step instructions...",
      "resources": ["..."],
      "success_criteria": "How to know if completed successfully"
    }}
  ]
}}
"""

HOMEWORK_PROMPT = ChatPromptTemplate.from_template(HOMEWORK_GENERATION_TEMPLATE)


# System message for general therapy assistance
THERAPY_ASSISTANT_SYSTEM_MESSAGE = SystemMessage(
    content="""You are a knowledgeable and empathetic clinical psychology assistant. You help therapists by:

1. Analyzing therapy session content objectively
2. Providing evidence-based recommendations
3. Maintaining strict confidentiality and professionalism
4. Focusing on therapeutic progress and patient wellbeing
5. Following ethical guidelines for mental health practice

Always prioritize patient safety and therapeutic effectiveness in your responses."""
)


def get_soap_prompt() -> ChatPromptTemplate:
    """Get SOAP note generation prompt."""
    return SOAP_PROMPT


def get_risk_assessment_prompt() -> ChatPromptTemplate:
    """Get risk assessment prompt."""
    return RISK_ASSESSMENT_PROMPT


def get_deidentification_prompt() -> PromptTemplate:
    """Get deidentification prompt."""
    return DEIDENTIFICATION_PROMPT


def get_homework_prompt() -> ChatPromptTemplate:
    """Get homework generation prompt."""
    return HOMEWORK_PROMPT


def get_system_message() -> SystemMessage:
    """Get system message for therapy assistant."""
    return THERAPY_ASSISTANT_SYSTEM_MESSAGE