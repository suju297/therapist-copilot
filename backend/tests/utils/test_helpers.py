"""Test utility functions and helpers."""

import json
import os
import tempfile
import time
import wave
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

import numpy as np
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from models.session import Session
from models.transcript import Transcript
from models.snippet import Snippet
from models.homework import Homework


fake = Faker()


class TestDataGenerator:
    """Generate realistic test data for therapy sessions."""
    
    @staticmethod
    def generate_session_data(
        therapist_id: Optional[str] = None,
        client_name: Optional[str] = None,
        status: str = "active"
    ) -> Dict[str, Any]:
        """Generate realistic session data."""
        return {
            "therapist_id": therapist_id or f"therapist_{fake.random_int(1, 100)}",
            "client_name": client_name or fake.name(),
            "session_type": fake.random_element(["individual", "group", "family"]),
            "status": status,
            "notes": fake.text(max_nb_chars=200) if fake.boolean() else None
        }
    
    @staticmethod
    def generate_transcript_data(
        session_id: UUID,
        speaker: str = "client",
        anxiety_level: str = "low"
    ) -> Dict[str, Any]:
        """Generate realistic transcript data based on anxiety level."""
        
        anxiety_phrases = {
            "low": [
                "I've been feeling okay lately.",
                "Work has been manageable this week.",
                "I'm looking forward to the weekend."
            ],
            "moderate": [
                "I've been feeling a bit anxious about the presentation.",
                "Sleep hasn't been great, but I'm managing.",
                "I worry sometimes about making mistakes."
            ],
            "high": [
                "I can't stop worrying about everything.",
                "I feel overwhelmed and don't know what to do.",
                "My anxiety is making it hard to function."
            ],
            "crisis": [
                "I can't take this anymore.",
                "Everything feels hopeless.",
                "I don't see a way out of this."
            ]
        }
        
        text = fake.random_element(anxiety_phrases[anxiety_level])
        
        return {
            "session_id": session_id,
            "text": text,
            "speaker": speaker,
            "confidence": fake.random.uniform(0.7, 0.98),
            "start_time": fake.random.uniform(0, 300),
            "end_time": fake.random.uniform(300, 600),
            "audio_duration": fake.random.uniform(2, 10)
        }
    
    @staticmethod
    def generate_snippet_data(category: str = "anxiety") -> Dict[str, Any]:
        """Generate CBT snippet data."""
        
        content_templates = {
            "anxiety": [
                "Practice deep breathing exercises when feeling anxious.",
                "Use the 5-4-3-2-1 grounding technique during panic attacks.",
                "Challenge catastrophic thoughts with evidence-based questioning."
            ],
            "depression": [
                "Schedule pleasant activities throughout your week.",
                "Practice gratitude by writing down three good things daily.",
                "Engage in behavioral activation through small, achievable goals."
            ],
            "mindfulness": [
                "Practice mindful breathing for 10 minutes daily.",
                "Use body scan meditation to increase awareness.",
                "Practice loving-kindness meditation for self-compassion."
            ]
        }
        
        return {
            "title": f"{category.title()} Management Technique",
            "content": fake.random_element(content_templates.get(category, content_templates["anxiety"])),
            "category": category,
            "intervention_type": fake.random_element(["cognitive", "behavioral", "mindfulness", "relaxation"]),
            "keywords": [category, "therapy", "coping"],
            "difficulty_level": fake.random_int(1, 5),
            "estimated_duration": fake.random_int(5, 60),
            "source": "Test CBT Manual",
            "evidence_level": "evidence-based"
        }
    
    @staticmethod
    def generate_homework_data(session_id: UUID, category: str = "general") -> Dict[str, Any]:
        """Generate homework assignment data."""
        
        homework_templates = {
            "anxiety": {
                "titles": ["Breathing Exercises", "Worry Time", "Exposure Practice"],
                "descriptions": [
                    "Practice daily breathing exercises",
                    "Set aside time for structured worrying",
                    "Gradually face feared situations"
                ]
            },
            "depression": {
                "titles": ["Activity Scheduling", "Gratitude Journal", "Social Connection"],
                "descriptions": [
                    "Plan and track daily activities",
                    "Write down things you're grateful for",
                    "Reach out to friends or family"
                ]
            }
        }
        
        template = homework_templates.get(category, homework_templates["anxiety"])
        
        return {
            "session_id": session_id,
            "title": fake.random_element(template["titles"]),
            "description": fake.random_element(template["descriptions"]),
            "category": category,
            "priority": fake.random_element(["low", "medium", "high"]),
            "estimated_duration": fake.random_int(10, 45),
            "instructions": fake.text(max_nb_chars=300)
        }


class AudioTestUtils:
    """Utilities for audio testing."""
    
    @staticmethod
    def create_test_audio(
        duration: float = 1.0,
        sample_rate: int = 16000,
        frequency: float = 440.0,
        amplitude: float = 0.3
    ) -> bytes:
        """Create test audio data as bytes."""
        
        # Generate sine wave
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Add some noise for realism
        noise = np.random.normal(0, 0.02, audio.shape)
        audio += noise
        
        # Convert to 16-bit integers
        audio_int16 = (audio * 32767).astype(np.int16)
        
        return audio_int16.tobytes()
    
    @staticmethod
    def create_test_wav_file(
        filepath: str,
        duration: float = 1.0,
        sample_rate: int = 16000,
        frequency: float = 440.0
    ) -> str:
        """Create a test WAV file."""
        
        audio_data = AudioTestUtils.create_test_audio(duration, sample_rate, frequency)
        
        with wave.open(filepath, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        return filepath
    
    @staticmethod
    def create_silent_audio(duration: float = 1.0, sample_rate: int = 16000) -> bytes:
        """Create silent audio data."""
        samples = int(sample_rate * duration)
        silence = np.zeros(samples, dtype=np.int16)
        return silence.tobytes()
    
    @staticmethod
    def create_noisy_audio(duration: float = 1.0, sample_rate: int = 16000) -> bytes:
        """Create noisy audio data (for testing error handling)."""
        samples = int(sample_rate * duration)
        noise = np.random.randint(-32768, 32767, samples, dtype=np.int16)
        return noise.tobytes()


class MockResponseGenerator:
    """Generate mock responses for AI services."""
    
    @staticmethod
    def mock_transcription_response(
        text: str = "Hello, how are you feeling today?",
        confidence: float = 0.9,
        has_speech: bool = True
    ) -> Dict[str, Any]:
        """Generate mock transcription response."""
        return {
            "text": text,
            "confidence": confidence,
            "language": "en",
            "duration": len(text.split()) * 0.5,  # Rough estimate
            "segments": [
                {
                    "start": 0.0,
                    "end": len(text.split()) * 0.5,
                    "text": text
                }
            ],
            "word_count": len(text.split()),
            "has_speech": has_speech
        }
    
    @staticmethod
    def mock_risk_assessment_response(
        risk_level: str = "low",
        score: float = 0.2
    ) -> Dict[str, Any]:
        """Generate mock risk assessment response."""
        return {
            "overall_risk_score": score,
            "risk_level": risk_level,
            "immediate_action_required": score >= 0.8,
            "crisis_keywords_detected": ["crisis"] if score >= 0.8 else [],
            "assessment_method": "mock",
            "risk_categories": {
                "suicide_risk": {"score": score * 0.8, "indicators": []},
                "self_harm_risk": {"score": score * 0.6, "indicators": []},
                "harm_to_others": {"score": score * 0.3, "indicators": []},
                "substance_abuse": {"score": score * 0.4, "indicators": []},
                "crisis_intervention": {"score": score, "indicators": []}
            },
            "recommendations": [
                "Continue monitoring" if score < 0.5 else "Immediate intervention required"
            ]
        }
    
    @staticmethod
    def mock_soap_response(
        subjective: str = "Client reports mild anxiety",
        objective: str = "Client appeared calm and engaged",
        assessment: str = "Mild situational anxiety",
        plan: str = "Continue with CBT techniques"
    ) -> Dict[str, Any]:
        """Generate mock SOAP note response."""
        return {
            "soap_note": {
                "subjective": subjective,
                "objective": objective,
                "assessment": assessment,
                "plan": plan
            },
            "homework_assignments": [
                {
                    "title": "Daily Breathing Exercise",
                    "description": "Practice 4-7-8 breathing technique twice daily",
                    "category": "anxiety",
                    "priority": "medium",
                    "estimated_duration": 10
                }
            ],
            "clinical_insights": {
                "primary_themes": ["anxiety", "coping"],
                "therapeutic_techniques_used": ["CBT", "breathing"],
                "patient_engagement_level": "high",
                "session_effectiveness": "high"
            }
        }


class DatabaseTestUtils:
    """Utilities for database testing."""
    
    @staticmethod
    async def create_test_session(
        db: AsyncSession,
        session_data: Optional[Dict[str, Any]] = None
    ) -> Session:
        """Create a test session in the database."""
        
        if session_data is None:
            session_data = TestDataGenerator.generate_session_data()
        
        session = Session(**session_data)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        return session
    
    @staticmethod
    async def create_test_transcripts(
        db: AsyncSession,
        session_id: UUID,
        count: int = 5,
        anxiety_level: str = "low"
    ) -> List[Transcript]:
        """Create multiple test transcripts."""
        
        transcripts = []
        
        for i in range(count):
            transcript_data = TestDataGenerator.generate_transcript_data(
                session_id=session_id,
                speaker="client" if i % 2 else "therapist",
                anxiety_level=anxiety_level
            )
            
            transcript = Transcript(**transcript_data)
            transcript.chunk_index = i
            
            db.add(transcript)
            transcripts.append(transcript)
        
        await db.commit()
        
        for transcript in transcripts:
            await db.refresh(transcript)
        
        return transcripts
    
    @staticmethod
    async def create_test_snippets(
        db: AsyncSession,
        categories: List[str] = None,
        count_per_category: int = 3
    ) -> List[Snippet]:
        """Create test CBT snippets."""
        
        if categories is None:
            categories = ["anxiety", "depression", "mindfulness"]
        
        snippets = []
        
        for category in categories:
            for _ in range(count_per_category):
                snippet_data = TestDataGenerator.generate_snippet_data(category)
                snippet = Snippet(**snippet_data)
                
                db.add(snippet)
                snippets.append(snippet)
        
        await db.commit()
        
        for snippet in snippets:
            await db.refresh(snippet)
        
        return snippets
    
    @staticmethod
    async def cleanup_test_data(db: AsyncSession, session_ids: List[UUID]):
        """Clean up test data from database."""
        from sqlalchemy import delete
        
        # Delete in correct order due to foreign key constraints
        await db.execute(delete(Homework).where(Homework.session_id.in_(session_ids)))
        await db.execute(delete(Transcript).where(Transcript.session_id.in_(session_ids)))
        await db.execute(delete(Session).where(Session.id.in_(session_ids)))
        
        await db.commit()


class WebSocketTestUtils:
    """Utilities for WebSocket testing."""
    
    @staticmethod
    def create_control_message(message_type: str, data: Dict[str, Any] = None) -> str:
        """Create a WebSocket control message."""
        message = {
            "type": message_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if data:
            message.update(data)
        
        return json.dumps(message)
    
    @staticmethod
    def parse_websocket_message(message_text: str) -> Dict[str, Any]:
        """Parse WebSocket message safely."""
        try:
            return json.loads(message_text)
        except json.JSONDecodeError:
            return {"type": "invalid", "raw": message_text}
    
    @staticmethod
    async def collect_websocket_messages(
        websocket,
        timeout: float = 5.0,
        max_messages: int = 10
    ) -> List[Dict[str, Any]]:
        """Collect WebSocket messages with timeout."""
        import asyncio
        
        messages = []
        
        async def collect():
            for _ in range(max_messages):
                try:
                    message = await websocket.receive_json()
                    messages.append(message)
                except:
                    break
        
        try:
            await asyncio.wait_for(collect(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        
        return messages


class PerformanceTestUtils:
    """Utilities for performance testing."""
    
    @staticmethod
    def time_function(func, *args, **kwargs):
        """Time function execution."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    async def time_async_function(func, *args, **kwargs):
        """Time async function execution."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    def measure_memory_usage():
        """Measure current memory usage."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # MB
    
    @staticmethod
    def create_load_test_data(count: int) -> List[Dict[str, Any]]:
        """Create data for load testing."""
        return [
            TestDataGenerator.generate_session_data()
            for _ in range(count)
        ]


class ValidationUtils:
    """Utilities for data validation in tests."""
    
    @staticmethod
    def validate_uuid(uuid_string: str) -> bool:
        """Validate UUID format."""
        try:
            UUID(uuid_string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_datetime(datetime_string: str) -> bool:
        """Validate ISO datetime format."""
        try:
            datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_soap_structure(soap_data: Dict[str, Any]) -> bool:
        """Validate SOAP note structure."""
        required_keys = ["subjective", "objective", "assessment", "plan"]
        
        if "soap_note" not in soap_data:
            return False
        
        soap_note = soap_data["soap_note"]
        
        return all(key in soap_note for key in required_keys)
    
    @staticmethod
    def validate_homework_structure(homework_data: Dict[str, Any]) -> bool:
        """Validate homework structure."""
        required_keys = ["title", "description", "category"]
        
        return all(key in homework_data for key in required_keys)
    
    @staticmethod
    def validate_risk_assessment_structure(risk_data: Dict[str, Any]) -> bool:
        """Validate risk assessment structure."""
        required_keys = [
            "overall_risk_score",
            "risk_level",
            "immediate_action_required",
            "risk_categories"
        ]
        
        return all(key in risk_data for key in required_keys)


# Export all utility classes for easy importing
__all__ = [
    "TestDataGenerator",
    "AudioTestUtils", 
    "MockResponseGenerator",
    "DatabaseTestUtils",
    "WebSocketTestUtils",
    "PerformanceTestUtils",
    "ValidationUtils"
]