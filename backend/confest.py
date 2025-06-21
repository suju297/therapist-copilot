"""Global test configuration and fixtures."""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

# Import the app and dependencies
from main import app
from deps.db import get_async_session, get_sync_session
from config import get_settings
from models import Session, Transcript, Snippet, Homework


# Test database configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture
def sync_engine():
    """Create sync test database engine."""
    engine = create_engine(
        TEST_SYNC_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    async_session_maker = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def sync_session(sync_engine) -> Generator:
    """Create sync database session for testing."""
    SessionLocal = sessionmaker(bind=sync_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client(async_session):
    """Create test client with overridden dependencies."""
    
    async def override_get_async_session():
        async with async_session as session:
            yield session
    
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_settings():
    """Create test settings."""
    return get_settings()


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_audio_data():
    """Generate sample audio data for testing."""
    import numpy as np
    
    # Generate 1 second of sample audio at 16kHz
    sample_rate = 16000
    duration = 1.0
    frequency = 440  # A note
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit integers
    audio_int16 = (audio * 32767).astype(np.int16)
    
    return audio_int16.tobytes()


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "therapist_id": "test_therapist",
        "client_name": "Test Client",
        "session_type": "individual",
        "status": "active"
    }


@pytest.fixture
def sample_transcript_data():
    """Sample transcript data for testing."""
    return {
        "text": "Hello, how are you feeling today?",
        "speaker": "therapist",
        "confidence": 0.95,
        "start_time": 0.0,
        "end_time": 2.5,
        "audio_duration": 2.5
    }


@pytest.fixture
def sample_snippet_data():
    """Sample CBT snippet data for testing."""
    return {
        "title": "Test Grounding Technique",
        "content": "This is a test grounding technique for anxiety management.",
        "category": "anxiety",
        "intervention_type": "grounding",
        "keywords": ["anxiety", "grounding", "test"],
        "difficulty_level": 1,
        "estimated_duration": 5,
        "source": "Test Source",
        "evidence_level": "evidence-based"
    }


@pytest.fixture
def sample_homework_data():
    """Sample homework data for testing."""
    return {
        "title": "Test Homework Assignment",
        "description": "Complete this test assignment for practice.",
        "category": "general",
        "priority": "medium",
        "estimated_duration": 15,
        "instructions": "Follow these test instructions carefully."
    }


@pytest.fixture
async def sample_session(async_session) -> Session:
    """Create a sample session in the database."""
    session_data = {
        "therapist_id": "test_therapist",
        "client_name": "Test Client",
        "session_type": "individual",
        "status": "active"
    }
    
    session = Session(**session_data)
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)
    
    return session


@pytest.fixture
async def sample_transcript(async_session, sample_session) -> Transcript:
    """Create a sample transcript in the database."""
    transcript_data = {
        "session_id": sample_session.id,
        "text": "Hello, how are you feeling today?",
        "speaker": "therapist",
        "confidence": 0.95,
        "start_time": 0.0,
        "end_time": 2.5,
        "audio_duration": 2.5
    }
    
    transcript = Transcript(**transcript_data)
    async_session.add(transcript)
    await async_session.commit()
    await async_session.refresh(transcript)
    
    return transcript


@pytest.fixture
async def sample_snippet(async_session) -> Snippet:
    """Create a sample snippet in the database."""
    snippet_data = {
        "title": "Test Grounding Technique",
        "content": "This is a test grounding technique for anxiety management.",
        "category": "anxiety",
        "intervention_type": "grounding",
        "keywords": ["anxiety", "grounding", "test"],
        "difficulty_level": 1,
        "estimated_duration": 5,
        "source": "Test Source",
        "evidence_level": "evidence-based"
    }
    
    snippet = Snippet(**snippet_data)
    async_session.add(snippet)
    await async_session.commit()
    await async_session.refresh(snippet)
    
    return snippet


@pytest.fixture
async def sample_homework(async_session, sample_session) -> Homework:
    """Create a sample homework assignment in the database."""
    homework_data = {
        "session_id": sample_session.id,
        "title": "Test Homework Assignment",
        "description": "Complete this test assignment for practice.",
        "category": "general",
        "priority": "medium",
        "estimated_duration": 15,
        "instructions": "Follow these test instructions carefully."
    }
    
    homework = Homework(**homework_data)
    async_session.add(homework)
    await async_session.commit()
    await async_session.refresh(homework)
    
    return homework


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "soap_note": {
            "subjective": "Client reports feeling anxious about upcoming presentation.",
            "objective": "Client appeared tense, fidgeting with hands.",
            "assessment": "Mild anxiety related to performance fears.",
            "plan": "Practice relaxation techniques and cognitive restructuring."
        },
        "homework_assignments": [
            {
                "title": "Daily Breathing Exercise",
                "description": "Practice 4-7-8 breathing technique twice daily.",
                "category": "anxiety",
                "priority": "high",
                "estimated_duration": 10,
                "instructions": "Inhale for 4, hold for 7, exhale for 8."
            }
        ],
        "clinical_insights": {
            "primary_themes": ["anxiety", "performance"],
            "therapeutic_techniques_used": ["CBT", "relaxation"],
            "patient_engagement_level": "high",
            "session_effectiveness": "high"
        }
    }


@pytest.fixture
def mock_risk_assessment():
    """Mock risk assessment response."""
    return {
        "overall_risk_score": 0.2,
        "risk_level": "low",
        "immediate_action_required": False,
        "crisis_keywords_detected": [],
        "assessment_method": "keyword_scan",
        "risk_categories": {
            "suicide_risk": {"score": 0.1, "indicators": []},
            "self_harm_risk": {"score": 0.0, "indicators": []},
            "harm_to_others": {"score": 0.0, "indicators": []},
            "substance_abuse": {"score": 0.1, "indicators": []},
            "crisis_intervention": {"score": 0.2, "indicators": []}
        },
        "recommendations": [
            "Continue standard care",
            "Maintain therapeutic relationship"
        ]
    }


@pytest.fixture
def mock_transcription_response():
    """Mock transcription response."""
    return {
        "text": "Hello, how are you feeling today?",
        "confidence": 0.95,
        "language": "en",
        "duration": 2.5,
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Hello, how are you feeling today?"
            }
        ],
        "word_count": 6,
        "has_speech": True
    }


@pytest.fixture
def auth_headers():
    """Authentication headers for testing."""
    return {"Authorization": "Bearer supersecret-dev-token"}


# Utility functions for tests
def create_test_audio_file(temp_dir: str, duration: float = 1.0) -> str:
    """Create a test audio file."""
    import wave
    import numpy as np
    
    filename = os.path.join(temp_dir, "test_audio.wav")
    sample_rate = 16000
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * 440 * t)  # 440 Hz tone
    audio_int16 = (audio * 32767).astype(np.int16)
    
    # Write WAV file
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    
    return filename


def assert_uuid_format(uuid_string: str):
    """Assert that a string is a valid UUID format."""
    from uuid import UUID
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False


def assert_datetime_format(datetime_string: str):
    """Assert that a string is a valid ISO datetime format."""
    from datetime import datetime
    try:
        datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False